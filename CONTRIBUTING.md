# Contributing to MarkItDown GUI

Thanks for your interest in contributing!

## Getting started

```bash
git clone https://github.com/ivansostarko/markitdown-gui.git
cd markitdown-gui
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the app with `markitdown-gui` or `python -m markitdown_gui`.

## Before you open a PR

1. **Lint:** `ruff check src tests` (and `ruff format` for formatting)
2. **Test:** `pytest`
3. Keep the UI layer (`app.py`) free of MarkItDown specifics — conversion logic belongs in `converter.py`.
4. One feature/fix per PR, with a clear description.

## Reporting bugs

Open an issue with your OS, Python version, the file type you converted, and the full error from the file row (hover) or terminal.

## Code of conduct

Be kind and constructive. Harassment or disrespect of any kind is not tolerated.
