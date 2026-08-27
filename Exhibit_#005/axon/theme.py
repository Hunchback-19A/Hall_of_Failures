"""Axon visual language.

A 2087 research notebook: ceramic tablets on a cloud-white desk.
This is a development environment, not a brain interface.
"""

from __future__ import annotations

import random
import sys
import tkinter as tk
from tkinter import ttk

# Desk (cloud white) and ceramic tablets sitting on it
DESK = "#F2F2ED"
WINDOW = DESK
CERAMIC = "#F7F6F1"
CERAMIC_HEADER = "#F3F2EC"
CERAMIC_RIM = "#D0CEC6"
CERAMIC_SHADOW = "#C5C3BB"
CERAMIC_LIP = "#E3E1D9"

PANEL = CERAMIC
PANEL_HEADER = CERAMIC_HEADER
EDITOR = CERAMIC
GUTTER = "#EEECE6"
OUTPUT = CERAMIC
INSET = "#E6E4DE"

INK = "#30302D"
INK_SOFT = "#6E6B63"
INK_FAINT = "#8a847a"

LINE = "#D5D3CC"
LINE_SOFT = "#E4E2DC"

# Restrained accents — laboratory sage, not neon
ACCENT = "#4d6a5e"
ACCENT_SOFT = "#6b8478"
STRUCTURAL = "#4a5f52"
NETWORK = "#3f5864"
FUNCTIONAL = "#675462"
STATE = "#7a5c3e"
COMMENT = "#8a7d72"
KEYWORD = "#506B82"
STRING = "#8A6A4A"
VERB = "#4a6358"
FORBIDDEN = "#7c4e48"
OK = "#728C72"
CONCEPTUAL = "#4A4A45"
SYSTEM = "#C96A2B"
SELECTION = "#D9E3E8"
WARN = SYSTEM
ERROR_LINE = "#f1e6dc"

CONCEPTUAL_ERRORS = frozenset(
    {"LabelError", "ProphecyError", "AttributionError", "SyntaxError"}
)
SYSTEM_ERRORS = frozenset({"CoordinateError", "ModelError", "ValueError", "CognitionError"})

SAFETY_LABELS = (
    "IDE, not brain interface.",
    "Modeling minds, not controlling them.",
)


def ui_font(size: int = 10, bold: bool = False):
    family = "Segoe UI" if sys.platform == "win32" else "Helvetica"
    return (family, size, "bold" if bold else "normal")


def mono_font(size: int = 12, bold: bool = False):
    family = "Consolas" if sys.platform == "win32" else "Courier"
    return (family, size, "bold" if bold else "normal")


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def ceramic_tile(
    master: tk.Misc,
    size: int = 72,
    base: str = CERAMIC,
    variation: int = 6,
    seed: int = 3,
) -> tk.PhotoImage:
    """A quiet clay grain — no glow, just a little material."""
    rng = random.Random(seed)
    red, green, blue = _rgb(base)
    rows: list[str] = []
    for y in range(size):
        thrown = 2 if y % 13 == 0 else 0
        cells: list[str] = []
        for x in range(size):
            noise = rng.randint(-variation, variation)
            grog = 10 if rng.random() < 0.012 else 0
            vein = 1 if (x + y * 2) % 29 == 0 else 0
            rr = max(0, min(255, red + noise - thrown - grog + vein))
            gg = max(0, min(255, green + noise - thrown - grog))
            bb = max(0, min(255, blue + noise - thrown - grog - vein))
            cells.append(f"#{rr:02x}{gg:02x}{bb:02x}")
        rows.append("{" + " ".join(cells) + "}")
    image = tk.PhotoImage(master=master, width=size, height=size)
    image.put(" ".join(rows))
    return image


def make_textures(master: tk.Misc) -> dict[str, tk.PhotoImage]:
    return {
        "desk": ceramic_tile(master, 84, DESK, variation=3, seed=1),
        "ceramic": ceramic_tile(master, 72, CERAMIC, variation=6, seed=7),
        "header": ceramic_tile(master, 72, CERAMIC_HEADER, variation=5, seed=4),
    }


def tile_canvas(canvas: tk.Canvas, tile: tk.PhotoImage) -> None:
    canvas.delete("grain")
    width = max(int(canvas.winfo_width()), 1)
    height = max(int(canvas.winfo_height()), 1)
    tw, th = tile.width(), tile.height()
    for x in range(0, width + tw, tw):
        for y in range(0, height + th, th):
            canvas.create_image(x, y, image=tile, anchor="nw", tags="grain")
    canvas.tag_lower("grain")


class CeramicTablet(tk.Frame):
    """A thin ceramic slab resting on the desk."""

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        textures: dict[str, tk.PhotoImage],
        on_hide=None,
    ) -> None:
        super().__init__(master, bg=DESK, highlightthickness=0, bd=0)
        self.on_hide = on_hide
        self._header_tile = textures["header"]
        self._body_tile = textures["ceramic"]

        # Thickness of the slab, then the glazed face
        shadow = tk.Frame(self, bg=CERAMIC_SHADOW, highlightthickness=0)
        shadow.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        face = tk.Frame(
            shadow,
            bg=CERAMIC,
            highlightbackground=CERAMIC_RIM,
            highlightcolor=CERAMIC_RIM,
            highlightthickness=1,
            bd=0,
        )
        face.pack(fill=tk.BOTH, expand=True)

        self._header = tk.Canvas(
            face,
            height=32,
            highlightthickness=0,
            bd=0,
            bg=CERAMIC_HEADER,
            cursor="arrow",
        )
        self._header.pack(fill=tk.X)
        self._header.bind("<Configure>", self._paint_header)
        self._title = title
        if on_hide:
            self._header.tag_bind("hide", "<Button-1>", lambda _e: on_hide())
            self._header.tag_bind("hide", "<Enter>", lambda _e: self._header.itemconfigure("hide", fill=INK_SOFT))
            self._header.tag_bind("hide", "<Leave>", lambda _e: self._header.itemconfigure("hide", fill=INK_FAINT))
            self._header.configure(cursor="hand2")

        lip = tk.Frame(face, bg=CERAMIC_LIP, height=1, highlightthickness=0)
        lip.pack(fill=tk.X)

        self.body = tk.Frame(face, bg=CERAMIC, highlightthickness=0)
        self.body.pack(fill=tk.BOTH, expand=True)

    def _paint_header(self, _event=None) -> None:
        canvas = self._header
        tile_canvas(canvas, self._header_tile)
        canvas.delete("fg")
        canvas.create_text(
            14,
            16,
            text=self._title,
            anchor="w",
            fill=INK,
            font=ui_font(9),
            tags="fg",
        )
        if self.on_hide:
            width = max(int(canvas.winfo_width()), 1)
            canvas.create_text(
                width - 14,
                16,
                text="Hide",
                anchor="e",
                fill=INK_FAINT,
                font=ui_font(9),
                tags=("fg", "hide"),
            )


def tree_rowheight(root: tk.Misc) -> int:
    """Row height that actually fits the UI font under Windows DPI."""
    from tkinter import font as tkfont

    measured = tkfont.Font(root=root, font=ui_font(10))
    return max(40, int(measured.metrics("linespace") + 22))


def apply(root: tk.Tk) -> ttk.Style:
    """Install the notebook theme on a Tk root."""
    root.configure(bg=DESK)
    root.option_add("*tearOff", False)
    root.option_add("*Font", ui_font(10))
    root.option_add("*Background", CERAMIC)
    root.option_add("*Foreground", INK)
    root.option_add("*selectBackground", SELECTION)
    root.option_add("*selectForeground", INK)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("TFrame", background=DESK)
    style.configure("Panel.TFrame", background=CERAMIC)
    style.configure("Header.TFrame", background=CERAMIC_HEADER)
    style.configure("Window.TFrame", background=DESK)

    style.configure(
        "TLabel",
        background=DESK,
        foreground=INK_SOFT,
        font=ui_font(9),
    )
    style.configure(
        "Title.TLabel",
        background=DESK,
        foreground=INK,
        font=ui_font(11),
    )
    style.configure(
        "Header.TLabel",
        background=CERAMIC_HEADER,
        foreground=INK_SOFT,
        font=ui_font(9),
        padding=(10, 7),
    )
    style.configure(
        "Safety.TLabel",
        background=DESK,
        foreground=ACCENT,
        font=ui_font(9),
    )
    style.configure(
        "Status.TLabel",
        background=DESK,
        foreground=INK_FAINT,
        font=ui_font(9),
        padding=(10, 6),
    )

    style.configure(
        "TButton",
        background=PANEL_HEADER,
        foreground=INK,
        font=ui_font(9),
        padding=(12, 5),
        borderwidth=1,
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", "#E4E4DF"), ("pressed", "#DEDED9")],
        foreground=[("active", INK)],
    )
    style.configure(
        "Accent.TButton",
        background="#d7e0d8",
        foreground=ACCENT,
        font=ui_font(9),
        padding=(14, 5),
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#c9d6cb"), ("pressed", "#bfd0c2")],
        foreground=[("active", ACCENT)],
    )

    style.configure(
        "TPanedwindow",
        background=DESK,
    )
    style.configure(
        "Sash",
        sashthickness=10,
        background=DESK,
    )

    style.configure(
        "Treeview",
        background=CERAMIC,
        fieldbackground=CERAMIC,
        foreground=INK,
        font=ui_font(10),
        rowheight=tree_rowheight(root),
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Treeview.Heading",
        background=CERAMIC_HEADER,
        foreground=INK_SOFT,
        font=ui_font(9),
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", SELECTION)],
        foreground=[("selected", INK)],
    )

    style.configure("TScrollbar", background=CERAMIC_HEADER, troughcolor=INSET, borderwidth=0)
    style.configure("TSeparator", background=LINE)
    return style
