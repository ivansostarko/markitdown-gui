"""Open the app with sample files, convert two of them and capture
docs/screenshot.png for the README. Windows/desktop only (uses ImageGrab).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from markitdown_gui.app import App  # noqa: E402

SAMPLES = {
    "quarterly-report.pdf": b"%PDF-1.4 placeholder",
    "presentation.pptx": b"placeholder",
    "sales-data.xlsx": b"placeholder",
    "meeting-notes.txt": b"# Meeting notes\n\n- Ship MarkItDown GUI v1.0\n- Celebrate\n",
    "landing-page.html": b"<html><body><h1>Landing page</h1><p>Hello!</p></body></html>",
}


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="mdgui_demo_"))
    paths = []
    for name, content in SAMPLES.items():
        p = tmp / name
        p.write_bytes(content)
        paths.append(p)

    import customtkinter as ctk

    ctk.set_appearance_mode("light")
    app = App()
    # Keep the window above everything else while we grab the screen region.
    app.attributes("-topmost", True)
    app.lift()
    app.focus_force()
    app.add_paths(paths)
    # Really convert the two formats that work without heavy dependencies.
    app.convert_one(paths[3])  # .txt
    app.convert_one(paths[4])  # .html

    def grab() -> None:
        app.update_idletasks()
        x, y = app.winfo_rootx(), app.winfo_rooty()
        w, h = app.winfo_width(), app.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        out = ROOT / "docs" / "screenshot.png"
        out.parent.mkdir(exist_ok=True)
        img.save(out)
        print(f"Saved {out} ({w}x{h})")
        app.destroy()

    app.after(4000, grab)
    app.mainloop()


if __name__ == "__main__":
    main()
