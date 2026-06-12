"""Conversion layer around Microsoft's MarkItDown.

Keeps all MarkItDown specifics out of the UI code so the engine can be
swapped, mocked in tests, or reused from the command line.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

#: Extensions MarkItDown can handle with the extras this project installs
#: (see ``dependencies`` in pyproject.toml).
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        # Documents
        ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
        # Plain / structured text
        ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".xml",
        # Web
        ".html", ".htm",
        # Notebooks & e-books
        ".ipynb", ".epub",
        # E-mail
        ".msg", ".eml",
        # Archives
        ".zip",
        # Images (metadata + OCR/description where available)
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        # Audio (metadata + speech transcription where available)
        ".mp3", ".wav", ".m4a",
    }
)

_markitdown = None  # lazily created singleton — importing markitdown is slow


def _engine():
    global _markitdown
    if _markitdown is None:
        from markitdown import MarkItDown

        _markitdown = MarkItDown(enable_plugins=False)
    return _markitdown


@dataclass(frozen=True)
class ConversionResult:
    source: Path
    output: Optional[Path]
    ok: bool
    error: Optional[str] = None


def is_supported(path: Union[str, Path]) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def convert_file(
    source: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
) -> ConversionResult:
    """Convert *source* to Markdown.

    The ``.md`` file is written next to the source file unless *output_dir*
    is given. An existing file with the same name is overwritten so that
    re-converting a document refreshes its Markdown.
    """
    source = Path(source)
    if not source.is_file():
        return ConversionResult(source, None, False, "File not found")
    if not is_supported(source):
        return ConversionResult(source, None, False, f"Unsupported file type: {source.suffix}")

    try:
        result = _engine().convert(str(source))
        target_dir = Path(output_dir) if output_dir else source.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{source.stem}.md"
        target.write_text(result.text_content, encoding="utf-8", newline="\n")
        return ConversionResult(source, target, True)
    except Exception as exc:  # MarkItDown raises a wide range of errors
        return ConversionResult(source, None, False, str(exc) or type(exc).__name__)
