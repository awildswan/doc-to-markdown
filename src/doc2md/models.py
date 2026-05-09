from dataclasses import dataclass, field


@dataclass
class ConvertResult:
    content: str
    source_format: str
    source_path: str
    metadata: dict = field(default_factory=dict)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.content)
