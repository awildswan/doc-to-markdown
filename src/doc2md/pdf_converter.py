import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from doc2md.models import ConvertResult

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}
MIN_TEXT_LENGTH = 50

_CN_PUNC = "，。、；：？！（）【】《》""''…—·"


# ---- Chinese OCR post-processing ----


def _clean_text(text: str) -> str:
    """Remove garbled lines from OCR output using jieba word segmentation."""
    try:
        import jieba
        _has_jieba = True
    except ImportError:
        _has_jieba = False

    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if _has_jieba:
            words = list(jieba.cut(stripped))
            valid = sum(1 for w in words if len(w) > 1)
            total = max(len(words), 1)
            if valid / total < 0.5:
                continue
        else:
            cn_chars = sum(1 for c in stripped if "一" <= c <= "鿿")
            total = max(len(stripped.replace(" ", "")), 1)
            if cn_chars / total < 0.3:
                continue
        cleaned.append(stripped)
    return "\n".join(cleaned)


# ---- Pixel-level preprocessing for black-and-white scanned documents ----


def _preprocess_pdf_pages(pdf_path: Path, work_dir: Path, dpi: int = 300,
                          text_threshold: int = 50) -> list[Path]:
    """
    Convert PDF pages to cleaned images for OCR.
    Pixel-level filtering for black-and-white scanned documents:
    1. Render at high DPI as grayscale
    2. Build mask: pixel <= threshold -> keep (text), else -> discard (noise/background)
    3. Apply mask to original: text keeps its value, background set to white (255)
    4. Remove remaining small noise specks via connected-component filtering
    """
    import fitz

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("opencv-python not available, falling back to raw rendering")
        return _render_pdf_pages_raw(pdf_path, work_dir, dpi)

    doc = fitz.open(str(pdf_path))
    image_paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2GRAY) if pix.n >= 3 else img

        # Otsu: adaptive threshold per-page, finds valley between text/background peaks
        otsu_thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Fallback to fixed threshold if Otsu gives unreasonable value
        effective_thresh = max(min(otsu_thresh, 120), text_threshold)
        mask = (gray <= effective_thresh)
        cleaned = np.where(mask, gray, 255).astype(np.uint8)

        # Remove specks: connected components with area < min_area
        binary_inv = (cleaned < 255).astype(np.uint8) * 255
        filtered = _remove_small_components(binary_inv, min_area=10)
        cleaned = cv2.bitwise_not(filtered)

        out_path = work_dir / f"page_{i:04d}.png"
        cv2.imwrite(str(out_path), cleaned)
        image_paths.append(out_path)

    doc.close()
    logger.info("Preprocessed %d pages (Otsu, clip=[%d,120], speck removal)",
                len(image_paths), text_threshold)
    return image_paths


def _remove_small_components(binary: "np.ndarray", min_area: int = 10) -> "np.ndarray":
    """Keep only connected components with area >= min_area pixels."""
    import cv2
    import numpy as np

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    mask = np.zeros_like(binary, dtype=np.uint8)
    for label_id in range(1, num_labels):
        if stats[label_id, cv2.CC_STAT_AREA] >= min_area:
            mask[labels == label_id] = 255
    return mask


def _render_pdf_pages_raw(pdf_path: Path, work_dir: Path, dpi: int = 300) -> list[Path]:
    import fitz

    doc = fitz.open(str(pdf_path))
    image_paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        out_path = work_dir / f"page_{i:04d}.png"
        pix.save(str(out_path))
        image_paths.append(out_path)
    doc.close()
    return image_paths


def _images_to_pdf(image_paths: list[Path], output_path: Path) -> Path:
    """Merge preprocessed page images back into a single PDF for MinerU."""
    import fitz

    doc = fitz.open()
    for ip in image_paths:
        img = fitz.open(str(ip))
        rect = img[0].rect
        page = doc.new_page(width=rect.width, height=rect.height)
        page.insert_image(rect, filename=str(ip))
        img.close()
    doc.save(str(output_path))
    doc.close()
    return output_path


# ---- PdfConverter ----


class PdfConverter:
    def __init__(self, timeout: int = 600, backend: str = "hybrid-auto-engine",
                 lang: str = "ch"):
        self.timeout = timeout
        self.backend = backend
        self.lang = lang

    def convert(self, path: str) -> ConvertResult:
        source_path = Path(path).resolve()
        ext = source_path.suffix.lower()

        if ext == ".pdf":
            text_content = self._extract_text_pymupdf(source_path)
            if text_content and len(text_content.strip()) >= MIN_TEXT_LENGTH:
                return ConvertResult(
                    content=text_content,
                    source_format="pdf",
                    source_path=str(path),
                    metadata={"engine": "pymupdf", "method": "text-extraction"},
                )
            logger.info("PDF has insufficient text layer, running OCR")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir).resolve()

            if ext == ".pdf":
                page_images = _preprocess_pdf_pages(source_path, tmpdir_path)
                merged_pdf = _images_to_pdf(page_images, tmpdir_path / "merged.pdf")
                ocr_input = merged_pdf
            elif ext in IMAGE_EXTENSIONS:
                ocr_input = source_path
            else:
                ocr_input = source_path

            content = self._run_ocr_single(ocr_input, tmpdir_path)
            content = _clean_text(content)

        return ConvertResult(
            content=content,
            source_format=ext.lstrip("."),
            source_path=str(path),
            metadata={
                "backend": self.backend,
                "engine": "mineru",
                "post_processed": True,
            },
        )

    def _run_ocr_single(self, input_path: Path, output_dir: Path) -> str:
        if shutil.which("mineru"):
            return self._run_local(input_path, output_dir)
        elif shutil.which("docker"):
            return self._run_docker(input_path, output_dir)
        else:
            raise RuntimeError("MinerU not found. Install: pip install 'mineru[all]'")

    def _run_local(self, input_path: Path, output_dir: Path) -> str:
        job_dir = output_dir / "output"
        job_dir.mkdir(exist_ok=True)
        cmd = [
            "mineru",
            "-p", str(input_path),
            "-o", str(job_dir),
            "-b", self.backend,
            "-l", self.lang,
        ]
        self._exec(cmd, str(input_path))

        md_files = list(job_dir.glob(f"**/{input_path.stem}*.md"))
        if not md_files:
            md_files = list(job_dir.glob("**/*.md"))
        if not md_files:
            raise RuntimeError(f"MinerU produced no .md output for {input_path}")

        return md_files[0].read_text(encoding="utf-8")

    def _run_docker(self, input_paths: list[Path], output_dir: Path) -> str:
        raise NotImplementedError("Docker mode not supported yet")

    def _exec(self, cmd: list[str], label: str) -> None:
        env = os.environ.copy()
        env.setdefault("MINERU_FORCE_VLM_OCR_ENABLE", "1")
        logger.info("Running: %s", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True, timeout=self.timeout,
                          capture_output=True, env=env)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"MinerU timed out after {self.timeout}s on {label}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"MinerU failed on {label}: {stderr}")

    def _extract_text_pymupdf(self, path: Path) -> str:
        try:
            import fitz
        except ImportError:
            return ""
        doc = fitz.open(str(path))
        parts = []
        for page in doc:
            text = page.get_text()
            if text:
                parts.append(text)
        doc.close()
        return "\n".join(parts)
