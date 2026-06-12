"""Tests for the conversion layer.

Conversion tests are skipped automatically when markitdown isn't installed,
so the suite stays green in minimal environments.
"""

from pathlib import Path

import pytest

from markitdown_gui.converter import SUPPORTED_EXTENSIONS, convert_file, is_supported

try:
    import markitdown  # noqa: F401

    HAS_MARKITDOWN = True
except ImportError:
    HAS_MARKITDOWN = False

needs_markitdown = pytest.mark.skipif(not HAS_MARKITDOWN, reason="markitdown not installed")


def test_supported_extensions_are_lowercase_with_dot():
    for ext in SUPPORTED_EXTENSIONS:
        assert ext.startswith(".")
        assert ext == ext.lower()


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report.PDF", True),
        ("slides.pptx", True),
        ("notes.txt", True),
        ("photo.jpeg", True),
        ("binary.exe", False),
        ("archive.rar", False),
        ("no_extension", False),
    ],
)
def test_is_supported(name, expected):
    assert is_supported(Path(name)) is expected


def test_convert_missing_file(tmp_path):
    result = convert_file(tmp_path / "ghost.pdf")
    assert not result.ok
    assert result.output is None
    assert "not found" in result.error.lower()


def test_convert_unsupported_type(tmp_path):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"MZ")
    result = convert_file(exe)
    assert not result.ok
    assert "unsupported" in result.error.lower()


@needs_markitdown
def test_convert_txt_roundtrip(tmp_path):
    src = tmp_path / "hello.txt"
    src.write_text("Hello **MarkItDown** GUI!", encoding="utf-8")
    result = convert_file(src)
    assert result.ok, result.error
    assert result.output == tmp_path / "hello.md"
    assert "MarkItDown" in result.output.read_text(encoding="utf-8")


@needs_markitdown
def test_convert_html_to_custom_output_dir(tmp_path):
    src = tmp_path / "page.html"
    src.write_text("<html><body><h1>Title</h1><p>Body text.</p></body></html>", encoding="utf-8")
    out_dir = tmp_path / "out"
    result = convert_file(src, output_dir=out_dir)
    assert result.ok, result.error
    assert result.output == out_dir / "page.md"
    text = result.output.read_text(encoding="utf-8")
    assert "Title" in text and "Body text." in text
