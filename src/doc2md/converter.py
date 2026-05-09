from pathlib import Path

from doc2md.excel_converter import ExcelConverter
from doc2md.models import ConvertResult
from doc2md.word_converter import WordConverter

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}


class UnsupportedFormatError(ValueError):
    pass


def convert(path: str, **kwargs) -> ConvertResult:
    ext = Path(path).suffix.lower()

    if ext in {".pdf"} | IMAGE_EXTENSIONS:
        from doc2md.pdf_converter import PdfConverter

        return PdfConverter(**kwargs).convert(path)
    elif ext == ".docx":
        return WordConverter().convert(path)
    elif ext in (".xlsx", ".xls"):
        return ExcelConverter().convert(path)
    else:
        raise UnsupportedFormatError(f"Unsupported format: {ext}")
