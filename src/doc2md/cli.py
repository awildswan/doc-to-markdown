import sys
from pathlib import Path

from doc2md.converter import UnsupportedFormatError, convert


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m doc2md <input> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    if not Path(input_path).exists():
        print(f"File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output = sys.argv[2] if len(sys.argv) > 2 else None
    if output is None:
        output = Path(input_path).with_suffix(".md")

    try:
        result = convert(input_path)
    except UnsupportedFormatError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    result.save(str(output))
    print(str(output))
