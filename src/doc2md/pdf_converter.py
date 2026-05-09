import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from doc2md.models import ConvertResult

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}
DOCKER_IMAGE = "opendatalab/mineru:latest"

MIN_TEXT_LENGTH = 50


class PdfConverter:
    def __init__(self, timeout: int = 300, backend: str = "pipeline"):
        self.timeout = timeout
        self.backend = backend

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
            logger.info("PDF has insufficient text layer, falling back to MinerU OCR")

        return self._convert_with_mineru(source_path, ext)

    def _extract_text_pymupdf(self, path: Path) -> str:
        try:
            import fitz
        except ImportError:
            logger.info("pymupdf not installed, skipping text extraction")
            return ""

        doc = fitz.open(str(path))
        parts = []
        for page in doc:
            text = page.get_text()
            if text:
                parts.append(text)
        doc.close()
        return "\n".join(parts)

    def _convert_with_mineru(self, source_path: Path, ext: str) -> ConvertResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir).resolve()

            if shutil.which("mineru"):
                engine = "mineru-cli"
                self._run_local(source_path, tmpdir_path)
            elif shutil.which("docker"):
                engine = "mineru-docker"
                self._run_docker(source_path, tmpdir_path)
            else:
                raise RuntimeError(
                    "MinerU not found. Install: pip install 'mineru[all]' "
                    "or pull docker image: docker pull opendatalab/mineru"
                )

            stem = source_path.stem
            md_candidates = list(tmpdir_path.glob(f"**/{stem}*.md"))
            if not md_candidates:
                md_candidates = list(tmpdir_path.glob("**/*.md"))

            if not md_candidates:
                raise RuntimeError(
                    f"MinerU did not produce any .md output for {source_path}"
                )

            content = md_candidates[0].read_text(encoding="utf-8")

        return ConvertResult(
            content=content,
            source_format=ext.lstrip("."),
            source_path=str(source_path),
            metadata={"backend": self.backend, "engine": engine},
        )

    def _run_local(self, input_path: Path, output_dir: Path) -> None:
        cmd = [
            "mineru",
            "-p", str(input_path),
            "-o", str(output_dir),
            "-b", self.backend,
        ]
        self._exec(cmd, str(input_path))

    def _run_docker(self, input_path: Path, output_dir: Path) -> None:
        input_dir = input_path.parent
        filename = input_path.name
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{input_dir}:/data/input:ro",
            "-v", f"{output_dir}:/data/output",
            DOCKER_IMAGE,
            "mineru",
            "-p", f"/data/input/{filename}",
            "-o", "/data/output",
            "-b", self.backend,
        ]
        self._exec(cmd, input_path.name)

    def _exec(self, cmd: list[str], label: str) -> None:
        logger.info("Running: %s", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True, timeout=self.timeout, capture_output=True)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"MinerU timed out after {self.timeout}s on {label}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"MinerU failed on {label}: {stderr}")
