"""MarkItDown GUI — main application window.

A modern CustomTkinter front-end for Microsoft's MarkItDown converter:
drop in (or browse for) any number of supported files and convert them —
one by one or all at once — into AI-ready Markdown.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from markitdown_gui import __app_name__, __version__
from markitdown_gui import updater
from markitdown_gui.converter import (
    SUPPORTED_EXTENSIONS,
    ConversionResult,
    convert_file,
    is_supported,
)

# Drag & drop is optional — the app works fine without tkinterdnd2.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    class _BaseWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

    _DND_AVAILABLE = True
except Exception:  # pragma: no cover - depends on local install
    _BaseWindow = ctk.CTk
    _DND_AVAILABLE = False


# ----------------------------------------------------------------- palette --
# Dark-gray accent; each pair is (light mode, dark mode).

ACCENT = ("#2f2f36", "#4b4b55")
ACCENT_HOVER = ("#45454e", "#5d5d68")
ACCENT_TEXT = ("#3f3f46", "#c6c6cf")
UPDATE_GREEN = "#22a05a"
UPDATE_GREEN_HOVER = "#1d8c4f"
SURFACE = ("#f4f4f6", "#1a1a1e")
CARD = ("#ffffff", "#232329")
CARD_BORDER = ("#e4e4e9", "#32323a")
TEXT_MUTED = ("#6b7280", "#9ca3af")

STATUS_STYLES = {
    "pending": ("#9ca3af", "Ready"),
    "converting": ("#f59e0b", "Converting…"),
    "done": ("#22c55e", "Done"),
    "error": ("#ef4444", "Failed"),
}

_BADGE_COLORS = {
    ".pdf": "#e2574c",
    ".docx": "#3b6fd4",
    ".pptx": "#d97a36",
    ".xlsx": "#3c9a5f",
    ".xls": "#3c9a5f",
    ".csv": "#3c9a5f",
    ".tsv": "#3c9a5f",
    ".html": "#8458d8",
    ".htm": "#8458d8",
    ".json": "#a8743c",
    ".xml": "#a8743c",
    ".ipynb": "#b8651f",
    ".epub": "#5f7d4f",
    ".zip": "#7a7a85",
    ".msg": "#4a90b8",
    ".eml": "#4a90b8",
    ".jpg": "#c34a8e",
    ".jpeg": "#c34a8e",
    ".png": "#c34a8e",
    ".gif": "#c34a8e",
    ".webp": "#c34a8e",
    ".mp3": "#2f9e9e",
    ".wav": "#2f9e9e",
    ".m4a": "#2f9e9e",
}

MAX_PARALLEL_CONVERSIONS = 2


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def _open_in_default_app(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ---------------------------------------------------------------- file row --


class FileRow(ctk.CTkFrame):
    """One file in the queue: badge, name, status and per-file actions."""

    def __init__(self, master, path: Path, on_convert, on_remove):
        super().__init__(
            master,
            fg_color=CARD,
            corner_radius=12,
            border_width=1,
            border_color=CARD_BORDER,
        )
        self.path = path
        self.status = "pending"
        self.result: ConversionResult | None = None
        self._on_convert = on_convert
        self._on_remove = on_remove

        self.grid_columnconfigure(1, weight=1)

        ext = path.suffix.lower()
        badge = ctk.CTkLabel(
            self,
            text=ext.lstrip(".").upper() or "?",
            width=56,
            height=30,
            corner_radius=8,
            fg_color=_BADGE_COLORS.get(ext, "#64748b"),
            text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        badge.grid(row=0, column=0, rowspan=2, padx=(12, 10), pady=12)

        name = ctk.CTkLabel(
            self,
            text=path.name,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        name.grid(row=0, column=1, sticky="ew", pady=(10, 0))

        try:
            size_text = _format_size(path.stat().st_size)
        except OSError:
            size_text = "?"
        self.meta_label = ctk.CTkLabel(
            self,
            text=f"{size_text}  ·  {path.parent}",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        )
        self.meta_label.grid(row=1, column=1, sticky="ew", pady=(0, 10))

        self.status_dot = ctk.CTkLabel(
            self, text="●", width=16, text_color=STATUS_STYLES["pending"][0]
        )
        self.status_dot.grid(row=0, column=2, rowspan=2, padx=(10, 0))
        self.status_label = ctk.CTkLabel(
            self,
            text=STATUS_STYLES["pending"][1],
            width=86,
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        )
        self.status_label.grid(row=0, column=3, rowspan=2, padx=(2, 6))

        self.action_btn = ctk.CTkButton(
            self,
            text="Convert",
            width=92,
            height=30,
            corner_radius=8,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_action,
        )
        self.action_btn.grid(row=0, column=4, rowspan=2, padx=(4, 6))

        self.remove_btn = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("#fee2e2", "#3b2430"),
            text_color=TEXT_MUTED,
            command=lambda: self._on_remove(self.path),
        )
        self.remove_btn.grid(row=0, column=5, rowspan=2, padx=(0, 10))

    # -- behaviour -----------------------------------------------------------

    def _on_action(self) -> None:
        if self.status == "done" and self.result and self.result.output:
            try:
                _open_in_default_app(self.result.output)
            except OSError as exc:
                messagebox.showerror(__app_name__, f"Could not open file:\n{exc}")
        else:
            self._on_convert(self.path)

    def set_status(self, status: str, result: ConversionResult | None = None) -> None:
        self.status = status
        self.result = result
        color, label = STATUS_STYLES[status]
        self.status_dot.configure(text_color=color)
        self.status_label.configure(text=label, text_color=color)

        if status == "converting":
            self.action_btn.configure(state="disabled", text="Working…")
            self.remove_btn.configure(state="disabled")
        elif status == "done":
            self.action_btn.configure(
                state="normal",
                text="Open .md",
                fg_color=UPDATE_GREEN,
                hover_color=UPDATE_GREEN_HOVER,
            )
            self.remove_btn.configure(state="normal")
            if result and result.output:
                self.meta_label.configure(text=f"→ {result.output}")
        elif status == "error":
            self.action_btn.configure(
                state="normal", text="Retry", fg_color=ACCENT, hover_color=ACCENT_HOVER
            )
            self.remove_btn.configure(state="normal")
            if result and result.error:
                short = result.error if len(result.error) < 120 else result.error[:117] + "…"
                self.meta_label.configure(text=f"⚠ {short}")
        else:  # pending
            self.action_btn.configure(
                state="normal", text="Convert", fg_color=ACCENT, hover_color=ACCENT_HOVER
            )
            self.remove_btn.configure(state="normal")


# ------------------------------------------------------------- about dialog --


class AboutDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master, fg_color=SURFACE)
        self.title(f"About {__app_name__}")
        self.geometry("440x460")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        card = ctk.CTkFrame(
            self, fg_color=CARD, corner_radius=16, border_width=1, border_color=CARD_BORDER
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            card,
            text="M↓",
            width=64,
            height=64,
            corner_radius=16,
            fg_color=ACCENT,
            text_color="#ffffff",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(pady=(28, 12))

        ctk.CTkLabel(
            card, text=__app_name__, font=ctk.CTkFont(size=20, weight="bold")
        ).pack()
        ctk.CTkLabel(
            card, text=f"Version {__version__}", font=ctk.CTkFont(size=12), text_color=TEXT_MUTED
        ).pack(pady=(2, 14))

        ctk.CTkLabel(
            card,
            text=(
                "A modern desktop GUI for Microsoft's MarkItDown.\n"
                "Converts PDF, Office, HTML, image and audio files into\n"
                "clean, AI-ready Markdown — fully local and offline."
            ),
            font=ctk.CTkFont(size=12),
            justify="center",
        ).pack(pady=(0, 12))

        ctk.CTkLabel(
            card,
            text="Author: Ivan Sostarko  ·  MIT License",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack()

        link = ctk.CTkLabel(
            card,
            text=updater.REPO_URL,
            font=ctk.CTkFont(size=12, underline=True),
            text_color=("#1f6feb", "#58a6ff"),
            cursor="hand2",
        )
        link.pack(pady=(4, 16))
        link.bind("<Button-1>", lambda _e: webbrowser.open(updater.REPO_URL))

        self.update_check_btn = ctk.CTkButton(
            card,
            text="Check for updates",
            width=180,
            height=34,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._check_updates,
        )
        self.update_check_btn.pack()

        self.update_status = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED
        )
        self.update_status.pack(pady=(6, 0))

        ctk.CTkButton(
            card,
            text="Close",
            width=90,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            text_color=TEXT_MUTED,
            hover_color=("#ececef", "#2a2a31"),
            command=self.destroy,
        ).pack(pady=(14, 0))

    def _check_updates(self) -> None:
        self.update_check_btn.configure(state="disabled", text="Checking…")
        self.update_status.configure(text="")
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self) -> None:
        info = updater.check_for_update()
        self.after(0, self._show_update_result, info)

    def _show_update_result(self, info: updater.UpdateInfo | None) -> None:
        if not self.winfo_exists():
            return
        if info is None:
            self.update_check_btn.configure(state="normal", text="Check for updates")
            self.update_status.configure(
                text="Could not reach GitHub — are you online?", text_color="#ef4444"
            )
        elif info.available:
            self.update_check_btn.configure(
                state="normal",
                text=f"Download {info.latest}",
                fg_color=UPDATE_GREEN,
                hover_color=UPDATE_GREEN_HOVER,
                command=lambda: webbrowser.open(info.url),
            )
            self.update_status.configure(
                text=f"New version {info.latest} is available!", text_color=UPDATE_GREEN
            )
        else:
            self.update_check_btn.configure(state="normal", text="Check for updates")
            self.update_status.configure(
                text=f"You are up to date (v{info.current}).", text_color=TEXT_MUTED
            )


# -------------------------------------------------------------- main window --


class App(_BaseWindow):
    def __init__(self):
        super().__init__(fg_color=SURFACE)
        self.title(f"{__app_name__} — Markdown for AI")
        self.geometry("980x680")
        self.minsize(760, 540)

        self.rows: dict[Path, FileRow] = {}
        self.output_dir: Path | None = None
        self._semaphore = threading.Semaphore(MAX_PARALLEL_CONVERSIONS)
        self._batch_total = 0
        self._batch_done = 0

        self._build_header()
        self._build_dropzone()
        self._build_file_list()
        self._build_footer()

        self.bind("<Control-o>", lambda _e: self.add_files_dialog())
        if _DND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)

        # Non-blocking update check; silently does nothing when offline.
        threading.Thread(target=self._startup_update_check, daemon=True).start()

    # -- layout ---------------------------------------------------------------

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        header.grid_columnconfigure(1, weight=1)

        logo = ctk.CTkLabel(
            header,
            text="M↓",
            width=46,
            height=46,
            corner_radius=12,
            fg_color=ACCENT,
            text_color="#ffffff",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        logo.grid(row=0, column=0, rowspan=2, padx=(0, 14))

        ctk.CTkLabel(
            header,
            text=__app_name__,
            anchor="w",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            header,
            text="Convert documents to clean, AI-ready Markdown — powered by Microsoft MarkItDown",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=1, sticky="w")

        self.update_btn = ctk.CTkButton(
            header,
            text="",
            width=132,
            height=30,
            corner_radius=8,
            fg_color=UPDATE_GREEN,
            hover_color=UPDATE_GREEN_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
        )  # hidden until a newer release is found

        self.theme_switch = ctk.CTkSegmentedButton(
            header,
            values=["Light", "Dark", "System"],
            command=lambda v: ctk.set_appearance_mode(v.lower()),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
        )
        self.theme_switch.set("Light")
        self.theme_switch.grid(row=0, column=3, rowspan=2, padx=(12, 0))

        ctk.CTkButton(
            header,
            text="About",
            width=72,
            height=30,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            text_color=ACCENT_TEXT,
            hover_color=("#ececef", "#2a2a31"),
            command=self.show_about,
        ).grid(row=0, column=4, rowspan=2, padx=(10, 0))

    def _build_dropzone(self) -> None:
        hint = "Drop files here, or click to browse" if _DND_AVAILABLE else "Click to browse for files"
        self.dropzone = ctk.CTkButton(
            self,
            text=f"⬆  {hint}\nPDF · Word · PowerPoint · Excel · HTML · images · audio · ZIP …",
            height=92,
            corner_radius=16,
            border_width=2,
            border_color=ACCENT,
            fg_color=CARD,
            hover_color=("#ececef", "#2a2a31"),
            text_color=ACCENT_TEXT,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.add_files_dialog,
        )
        self.dropzone.pack(fill="x", padx=24, pady=(8, 12))

    def _build_file_list(self) -> None:
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            label_text="",
        )
        self.list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="No files yet — add some to get started.",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
        )
        self.empty_label.pack(pady=48)

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(
            self, fg_color=CARD, corner_radius=16, border_width=1, border_color=CARD_BORDER
        )
        footer.pack(fill="x", padx=24, pady=(4, 20))
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            footer,
            text="Output folder",
            width=120,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            text_color=("#374151", "#d1d5db"),
            hover_color=("#ececf6", "#262637"),
            command=self.choose_output_dir,
        ).grid(row=0, column=0, padx=(14, 10), pady=12)

        self.output_label = ctk.CTkLabel(
            footer,
            text="Saving next to each source file",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        )
        self.output_label.grid(row=0, column=1, sticky="ew")

        self.progress = ctk.CTkProgressBar(footer, height=8, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 4))

        self.summary_label = ctk.CTkLabel(
            footer, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED
        )
        self.summary_label.grid(row=2, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 8))

        self.clear_btn = ctk.CTkButton(
            footer,
            text="Clear list",
            width=96,
            height=36,
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            border_color=CARD_BORDER,
            text_color=TEXT_MUTED,
            hover_color=("#fee2e2", "#3b2430"),
            command=self.clear_all,
        )
        self.clear_btn.grid(row=0, column=2, padx=(10, 8), pady=12)

        self.convert_all_btn = ctk.CTkButton(
            footer,
            text="Convert all  →",
            width=150,
            height=36,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.convert_all,
        )
        self.convert_all_btn.grid(row=0, column=3, padx=(0, 14), pady=12)

    # -- adding & removing files ----------------------------------------------

    def add_files_dialog(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="Choose files to convert",
            filetypes=[("Supported files", patterns), ("All files", "*.*")],
        )
        if paths:
            self.add_paths(paths)

    def _on_drop(self, event) -> None:
        self.add_paths(self.tk.splitlist(event.data))

    def add_paths(self, paths) -> None:
        skipped: list[str] = []
        for raw in paths:
            path = Path(raw)
            if path.is_dir():
                children = [p for p in sorted(path.rglob("*")) if p.is_file() and is_supported(p)]
                if children:
                    self.add_paths(children)
                else:
                    skipped.append(path.name)
                continue
            if path in self.rows:
                continue
            if not is_supported(path):
                skipped.append(path.name)
                continue
            row = FileRow(self.list_frame, path, on_convert=self.convert_one, on_remove=self.remove_one)
            row.pack(fill="x", pady=4, padx=4)
            self.rows[path] = row

        self._refresh_empty_state()
        self._update_summary()
        if skipped:
            shown = "\n".join(skipped[:8]) + ("\n…" if len(skipped) > 8 else "")
            messagebox.showwarning(
                __app_name__, f"Skipped {len(skipped)} unsupported item(s):\n\n{shown}"
            )

    def remove_one(self, path: Path) -> None:
        row = self.rows.pop(path, None)
        if row is not None:
            row.destroy()
        self._refresh_empty_state()
        self._update_summary()

    def clear_all(self) -> None:
        if any(row.status == "converting" for row in self.rows.values()):
            messagebox.showinfo(__app_name__, "Please wait for running conversions to finish.")
            return
        for row in list(self.rows.values()):
            row.destroy()
        self.rows.clear()
        self.progress.set(0)
        self._refresh_empty_state()
        self._update_summary()

    def _refresh_empty_state(self) -> None:
        if self.rows:
            self.empty_label.pack_forget()
        else:
            self.empty_label.pack(pady=48)

    # -- output folder ----------------------------------------------------------

    def choose_output_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Choose output folder (Cancel = next to source)")
        if chosen:
            self.output_dir = Path(chosen)
            self.output_label.configure(text=f"Saving to: {self.output_dir}")
        else:
            self.output_dir = None
            self.output_label.configure(text="Saving next to each source file")

    # -- conversion ---------------------------------------------------------------

    def convert_one(self, path: Path) -> None:
        self._start_batch([path])

    def convert_all(self) -> None:
        pending = [p for p, row in self.rows.items() if row.status in ("pending", "error")]
        if not pending:
            messagebox.showinfo(__app_name__, "Nothing to convert — add some files first.")
            return
        self._start_batch(pending)

    def _start_batch(self, paths: list[Path]) -> None:
        runnable = [p for p in paths if p in self.rows and self.rows[p].status != "converting"]
        if not runnable:
            return
        if self._batch_done >= self._batch_total:  # previous batch finished — reset
            self._batch_total = 0
            self._batch_done = 0
        self._batch_total += len(runnable)
        self._update_summary()
        for path in runnable:
            self.rows[path].set_status("converting")
            threading.Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path: Path) -> None:
        with self._semaphore:
            result = convert_file(path, self.output_dir)
        self.after(0, self._on_result, path, result)

    def _on_result(self, path: Path, result: ConversionResult) -> None:
        self._batch_done += 1
        row = self.rows.get(path)
        if row is not None:
            row.set_status("done" if result.ok else "error", result)
        self.progress.set(self._batch_done / self._batch_total if self._batch_total else 0)
        self._update_summary()

    # -- about & updates ------------------------------------------------------------

    def show_about(self) -> None:
        AboutDialog(self)

    def _startup_update_check(self) -> None:
        info = updater.check_for_update()
        if info is not None and info.available:
            self.after(0, self._show_update_available, info)

    def _show_update_available(self, info: updater.UpdateInfo) -> None:
        self.update_btn.configure(
            text=f"⬆  Update to {info.latest}",
            command=lambda: webbrowser.open(info.url),
        )
        self.update_btn.grid(row=0, column=2, rowspan=2, padx=(12, 0))

    # -- summary ------------------------------------------------------------------

    def _update_summary(self) -> None:
        total = len(self.rows)
        done = sum(1 for r in self.rows.values() if r.status == "done")
        failed = sum(1 for r in self.rows.values() if r.status == "error")
        running = sum(1 for r in self.rows.values() if r.status == "converting")
        parts = [f"{total} file(s) in queue"]
        if running:
            parts.append(f"{running} converting")
        if done:
            parts.append(f"{done} done")
        if failed:
            parts.append(f"{failed} failed")
        parts.append(f"v{__version__}")
        self.summary_label.configure(text="   ·   ".join(parts))


def main() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
