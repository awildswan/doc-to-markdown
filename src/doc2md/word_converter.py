from pathlib import Path

import mammoth

from doc2md.models import ConvertResult


class WordConverter:
    def convert(self, path: str) -> ConvertResult:
        with open(path, "rb") as f:
            result = mammoth.convert_to_markdown(f)
        if result.messages:
            warnings = [str(m) for m in result.messages]
        else:
            warnings = []
        return ConvertResult(
            content=result.value,
            source_format="docx",
            source_path=str(path),
            metadata={"warnings": warnings},
        )
