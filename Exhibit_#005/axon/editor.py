"""Axon — Ranvier Editor v0.1

A calm 2087 research notebook for .cog programs.

Axon is not a brain interface, not a cockpit, and not an oracle.
It is a scientific development environment: write, validate, and run models.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import ranvier
from ranvier.compiler import MODEL_FILES
from ranvier.errors import CognitionError
from ranvier.parser import AssociateStmt, LoadStmt, ParseError, parse

from . import diagnostics, runner, syntax, theme, viewer

APP_NAME = "Axon"
APP_VERSION = "0.1"
PHILOSOPHY = "Never compile a destiny when you only measured a state."
DEFAULT_EXT = ".cog"
FILE_TYPES = [("Ranvier files", "*.cog"), ("All files", "*.*")]
APP_USER_MODEL_ID = "Ranvier.Axon"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TITLEBAR_ICON_PATH = Path(__file__).resolve().parent / "jellyfish.ico"
APP_ICON_ICO = PROJECT_ROOT / "Icon.ico"
APP_ICON_PNG = PROJECT_ROOT / "Icon.png"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
UNTITLED = f"blank_slate{DEFAULT_EXT}"

MODEL_ALIASES = {
    "atlas": "brain_atlas.json",
    "brain_atlas": "brain_atlas.json",
    "structure": "brain_atlas.json",
    "connectivity": "brain_connectivity.json",
    "brain_connectivity": "brain_connectivity.json",
    "function": "brain_function.json",
    "functions": "brain_function.json",
    "brain_function": "brain_function.json",
    "behavior": "brain_behavior.json",
    "behaviour": "brain_behavior.json",
    "brain_behavior": "brain_behavior.json",
}

MODEL_ROLES = {
    "brain_atlas.json": "physical structure",
    "brain_connectivity.json": "pathways and networks",
    "brain_function.json": "network processes",
    "brain_behavior.json": "observed outcomes",
}

def new_file_template() -> str:
    version = getattr(ranvier, "__version__", APP_VERSION)
    released = getattr(ranvier, "__release_date__", "")
    stamp = f" v{version} ({released})" if released else f" v{version}"
    return (
        f"# Welcome to Ranvier{stamp}\n"
        "# Begin by describing, not assuming.\n"
        '# Type Help > About Axon for more information.\n'
        "\n"
        "load atlas\n"
        "load connectivity\n"
        "load function\n"
        "load behavior\n"
        "\n"
    )


def _prefer_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            from ctypes import windll

            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _claim_windows_identity() -> None:
    """Tell Windows this process is Axon, not a generic python.exe window."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


_GDI_TOKEN = None


def _windows_hwnds(window: tk.Misc) -> list[int]:
    hwnds: list[int] = []
    try:
        from ctypes import windll

        user32 = windll.user32
        child = int(window.winfo_id())
        hwnds.append(child)
        parent = int(user32.GetParent(child) or 0)
        if parent:
            hwnds.append(parent)
        root = int(user32.GetAncestor(child, 2) or 0)
        if root:
            hwnds.append(root)
        frame = window.wm_frame()
        if frame:
            hwnds.append(int(frame, 16))
    except Exception:
        pass
    seen: set[int] = set()
    unique: list[int] = []
    for hwnd in hwnds:
        if hwnd and hwnd not in seen:
            seen.add(hwnd)
            unique.append(hwnd)
    return unique


def _gdiplus_startup() -> bool:
    global _GDI_TOKEN
    if _GDI_TOKEN is not None:
        return True
    try:
        import ctypes

        class StartupInput(ctypes.Structure):
            _fields_ = [
                ("GdiplusVersion", ctypes.c_uint32),
                ("DebugEventCallback", ctypes.c_void_p),
                ("SuppressBackgroundThread", ctypes.c_int),
                ("SuppressExternalCodecs", ctypes.c_int),
            ]

        gdiplus = ctypes.windll.gdiplus
        token = ctypes.c_ulonglong(0)
        startup = StartupInput(1, None, 0, 0)
        gdiplus.GdiplusStartup.restype = ctypes.c_int
        if gdiplus.GdiplusStartup(ctypes.byref(token), ctypes.byref(startup), None) != 0:
            return False
        _GDI_TOKEN = token
        return True
    except Exception:
        return False


def _window_icon_sizes() -> tuple[int, int]:
    if sys.platform != "win32":
        return 16, 32
    try:
        from ctypes import windll

        small = int(windll.user32.GetSystemMetrics(49) or 16)
        big = int(windll.user32.GetSystemMetrics(11) or 32)
        return max(small, 16), max(big, 32)
    except Exception:
        return 16, 32


def _hicon_from_image(path: Path, size: int) -> int:
    if not path.is_file() or not _gdiplus_startup():
        return 0
    try:
        import ctypes
        from ctypes import wintypes

        gdiplus = ctypes.windll.gdiplus
        bitmap = ctypes.c_void_p()
        gdiplus.GdipCreateBitmapFromFile.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p)]
        gdiplus.GdipCreateBitmapFromFile.restype = ctypes.c_int
        if gdiplus.GdipCreateBitmapFromFile(str(path.resolve()), ctypes.byref(bitmap)) != 0:
            return 0
        handle = wintypes.HICON()
        gdiplus.GdipCreateHICONFromBitmap.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.HICON)]
        gdiplus.GdipCreateHICONFromBitmap.restype = ctypes.c_int
        status = gdiplus.GdipCreateHICONFromBitmap(bitmap, ctypes.byref(handle))
        gdiplus.GdipDisposeImage(bitmap)
        if status != 0 or not handle:
            return 0
        copied = ctypes.windll.user32.CopyImage(handle, 1, size, size, 0)
        if copied:
            ctypes.windll.user32.DestroyIcon(handle)
            return int(copied)
        return int(handle)
    except Exception:
        return 0


def _hicon_from_png(path: Path, size: int) -> int:
    return _hicon_from_image(path, size)


def _hicon_from_ico(path: Path, size: int) -> int:
    if not path.is_file():
        return 0
    try:
        from ctypes import windll

        handle = windll.user32.LoadImageW(
            None, str(path.resolve()), 1, size, size, 0x0010 | 0x2000
        )
        if handle:
            return int(handle)
    except Exception:
        pass
    return _hicon_from_image(path, size)


def _app_identity_ico() -> Path | None:
    """Icon.ico in the project — the same path every machine gets from GitHub."""
    return APP_ICON_ICO if APP_ICON_ICO.is_file() else None


def _windows_set_hicon(window: tk.Misc, handle: int, *, big: bool) -> None:
    if sys.platform != "win32" or not handle:
        return
    try:
        from ctypes import windll

        which = 1 if big else 0
        for hwnd in _windows_hwnds(window):
            windll.user32.SendMessageW(hwnd, 0x0080, which, handle)
    except Exception:
        pass


def _pythonw_path() -> Path:
    exe = Path(sys.executable)
    windowed = exe.with_name("pythonw.exe")
    return windowed if windowed.is_file() else exe


_GUID_CLS = None


def _guid_cls():
    global _GUID_CLS
    if _GUID_CLS is None:
        import ctypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_uint32),
                ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        _GUID_CLS = GUID
    return _GUID_CLS


def _guid(data1: int, data2: int, data3: int, data4: tuple[int, ...]):
    value = _guid_cls()()
    value.Data1 = data1
    value.Data2 = data2
    value.Data3 = data3
    value.Data4[:] = data4
    return value


def _set_window_app_id(window: tk.Misc, icon_path: Path | None) -> list[object]:
    """Taskbar uses AppUserModel properties; the caption can keep a different icon."""
    keep: list[object] = []
    if sys.platform != "win32":
        return keep
    try:
        import ctypes
        from ctypes import wintypes

        guid_type = _guid_cls()

        class PROPERTYKEY(ctypes.Structure):
            _fields_ = [
                ("fmtid", guid_type),
                ("pid", ctypes.c_uint32),
            ]

        class PROPVARIANT(ctypes.Structure):
            class _Union(ctypes.Union):
                _fields_ = [("pwszVal", ctypes.c_void_p)]

            _anonymous_ = ("_u",)
            _fields_ = [
                ("vt", ctypes.c_ushort),
                ("wReserved1", ctypes.c_ushort),
                ("wReserved2", ctypes.c_ushort),
                ("wReserved3", ctypes.c_ushort),
                ("_u", _Union),
            ]

        fmtid = _guid(0x9F4C2855, 0x9F79, 0x4B39, (0xA8, 0xD0, 0xE1, 0xD4, 0x2D, 0xE1, 0xD5, 0xF3))
        iid = _guid(0x886D8EEB, 0x8CF2, 0x4446, (0x8D, 0x02, 0xCD, 0xBA, 0x1D, 0xBD, 0xCF, 0x99))
        shell32 = ctypes.windll.shell32
        shell32.SHGetPropertyStoreForWindow.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(guid_type),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        shell32.SHGetPropertyStoreForWindow.restype = ctypes.HRESULT

        pythonw = _pythonw_path()
        launcher = PROJECT_ROOT / "Axon.pyw"
        command = f'"{pythonw}" "{launcher}"' if launcher.is_file() else f'"{pythonw}" -m axon'
        values = {
            5: APP_USER_MODEL_ID,
            2: command,
            4: APP_NAME,
        }
        if icon_path is not None and icon_path.is_file():
            values[3] = str(icon_path.resolve())

        def vtbl(obj, index, *argtypes):
            this = ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))
            table = ctypes.cast(this[0], ctypes.POINTER(ctypes.c_void_p))
            func = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argtypes)(table[index])
            return lambda *args: func(obj, *args)

        for hwnd in _windows_hwnds(window):
            store = ctypes.c_void_p()
            if shell32.SHGetPropertyStoreForWindow(hwnd, ctypes.byref(iid), ctypes.byref(store)) != 0 or not store:
                continue
            set_value = vtbl(store, 6, ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))
            commit = vtbl(store, 7)
            release = vtbl(store, 2)
            for pid, text in values.items():
                key = PROPERTYKEY()
                key.fmtid = fmtid
                key.pid = pid
                buf = ctypes.create_unicode_buffer(text)
                keep.append(buf)
                variant = PROPVARIANT()
                variant.vt = 31
                variant.pwszVal = ctypes.cast(buf, ctypes.c_void_p)
                set_value(ctypes.byref(key), ctypes.byref(variant))
            commit()
            release()
    except Exception:
        pass
    return keep


class AxonEditor:
    def __init__(self, root: tk.Tk, path: Path | None = None) -> None:
        self.root = root
        self.path: Path | None = None
        self._dirty = False
        self._app_icon_photo: tk.PhotoImage | None = None
        self._hicon_app = 0
        self._hicon_title = 0
        self._identity_keep: list[object] = []
        self._highlight_job: str | None = None
        self._safety_index = 0
        self._project_nodes: dict[str, tuple[str, Path | None]] = {}

        theme.apply(root)
        self._textures = theme.make_textures(root)
        self._pane_vars = {
            "project": tk.BooleanVar(master=root, value=True),
            "editor": tk.BooleanVar(master=root, value=True),
            "models": tk.BooleanVar(master=root, value=True),
            "output": tk.BooleanVar(master=root, value=True),
        }
        self._build()
        self._refresh_project()
        if path and path.exists():
            self._open_path(path)
        else:
            self._new_buffer(clear_to_template=True)
        self._tick_safety()

    def _build(self) -> None:
        self.root.title(self._title())
        self._apply_icon()
        self.root.geometry("1280x800")
        self.root.minsize(960, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self._desk = tk.Canvas(self.root, bg=theme.DESK, highlightthickness=0, bd=0)
        self._desk.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._desk.bind("<Configure>", lambda _e: theme.tile_canvas(self._desk, self._textures["desk"]))

        self._build_menu()
        self._build_chrome()
        self._build_status()

        self.outer = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        self.outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 2))

        self.columns = ttk.Panedwindow(self.outer, orient=tk.HORIZONTAL)
        self.project_tablet = theme.CeramicTablet(
            self.columns, "Project", self._textures, on_hide=lambda: self._hide_pane("project")
        )
        self.editor_tablet = theme.CeramicTablet(
            self.columns, "Antechamber (Editor)", self._textures, on_hide=lambda: self._hide_pane("editor")
        )
        self.model_tablet = theme.CeramicTablet(
            self.columns, "Pillar Crypts (Models)", self._textures, on_hide=lambda: self._hide_pane("models")
        )
        self.output_tablet = theme.CeramicTablet(
            self.outer, "Megaron (Output)", self._textures, on_hide=lambda: self._hide_pane("output")
        )

        self.outer.add(self.columns, weight=5)
        self.outer.add(self.output_tablet, weight=2)
        self.columns.add(self.project_tablet, weight=1)
        self.columns.add(self.editor_tablet, weight=4)
        self.columns.add(self.model_tablet, weight=2)

        self._build_project(self.project_tablet.body)
        self._build_editor(self.editor_tablet.body)
        self._build_model_panel(self.model_tablet.body)
        self._build_output(self.output_tablet.body)
        self._raise_chrome()

        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_file_as())
        self.root.bind("<F5>", lambda e: self.run_file())
        self.root.bind("<Control-r>", lambda e: self.run_file())
        self.root.bind("<Control-Key-1>", lambda e: self._toggle_pane("project"))
        self.root.bind("<Control-Key-2>", lambda e: self._toggle_pane("editor"))
        self.root.bind("<Control-Key-3>", lambda e: self._toggle_pane("models"))
        self.root.bind("<Control-Key-4>", lambda e: self._toggle_pane("output"))

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root, background=theme.DESK, foreground=theme.INK, activebackground=theme.INSET)
        file_menu = tk.Menu(menubar)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Refresh project", command=self._refresh_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        run_menu = tk.Menu(menubar)
        run_menu.add_command(label="Run", accelerator="F5", command=self.run_file)
        menubar.add_cascade(label="Run", menu=run_menu)

        view_menu = tk.Menu(menubar)
        view_menu.add_checkbutton(
            label="Project",
            variable=self._pane_vars["project"],
            command=self._sync_panes,
            accelerator="Ctrl+1",
        )
        view_menu.add_checkbutton(
            label="Antechamber (Editor)",
            variable=self._pane_vars["editor"],
            command=self._sync_panes,
            accelerator="Ctrl+2",
        )
        view_menu.add_checkbutton(
            label="Pillar Crypts (Models)",
            variable=self._pane_vars["models"],
            command=self._sync_panes,
            accelerator="Ctrl+3",
        )
        view_menu.add_checkbutton(
            label="Megaron (Output)",
            variable=self._pane_vars["output"],
            command=self._sync_panes,
            accelerator="Ctrl+4",
        )
        view_menu.add_separator()
        view_menu.add_command(label="Model viewer (later)...", command=self.show_viewer_placeholder)
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar)
        help_menu.add_command(label="About Axon", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def _build_chrome(self) -> None:
        bar = ttk.Frame(self.root, style="Window.TFrame")
        bar.pack(fill=tk.X, padx=12, pady=(10, 8))

        ttk.Label(bar, text="Axon", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(bar, text="  Ranvier notebook", style="TLabel").pack(side=tk.LEFT, padx=(4, 0))

        ttk.Button(bar, text="Run", style="Accent.TButton", command=self.run_file).pack(side=tk.RIGHT)
        ttk.Button(bar, text="Save", command=self.save_file).pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Button(bar, text="Open", command=self.open_file).pack(side=tk.RIGHT, padx=(0, 6))
        ttk.Button(bar, text="New", command=self.new_file).pack(side=tk.RIGHT, padx=(0, 6))

    def _build_project(self, parent) -> None:
        tree_wrap = tk.Frame(parent, bg=theme.CERAMIC, highlightthickness=0)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(tree_wrap)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree = ttk.Treeview(
            tree_wrap,
            show="tree",
            selectmode="browse",
            yscrollcommand=scroll.set,
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=(4, 8))
        self.tree.configure(style="Treeview")
        style = ttk.Style(self.tree)
        style.configure("Treeview", rowheight=theme.tree_rowheight(self.root), font=theme.ui_font(10))
        scroll.config(command=self.tree.yview)
        self.tree.bind("<<TreeviewSelect>>", self._on_project_select)
        self.tree.bind("<Double-1>", self._on_project_open)

    def _build_editor(self, parent) -> None:
        wrap = tk.Frame(parent, bg=theme.EDITOR, highlightthickness=0)
        wrap.pack(fill=tk.BOTH, expand=True)

        self.linenumbers = tk.Text(
            wrap,
            width=5,
            padx=8,
            takefocus=0,
            border=0,
            background=theme.GUTTER,
            foreground=theme.INK_FAINT,
            font=theme.mono_font(12),
            state=tk.DISABLED,
            wrap=tk.NONE,
            cursor="arrow",
        )
        self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)

        scroll = ttk.Scrollbar(wrap)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text = tk.Text(
            wrap,
            wrap=tk.NONE,
            undo=True,
            font=theme.mono_font(12),
            background=theme.EDITOR,
            foreground=theme.INK,
            insertbackground=theme.INK_SOFT,
            selectbackground=theme.SELECTION,
            selectforeground=theme.INK,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=14,
            pady=10,
            spacing1=1,
            spacing3=3,
            yscrollcommand=lambda *args: self._on_text_scroll(*args, scrollbar=scroll),
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self._on_scrollbar)

        syntax.configure_tags(self.text, theme.mono_font(12, bold=True))
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<KeyRelease>", self._schedule_highlight)
        self.text.bind("<ButtonRelease-1>", lambda e: self._refresh_line_numbers())

    def _build_model_panel(self, parent) -> None:
        self.models = tk.Text(
            parent,
            wrap=tk.WORD,
            font=theme.ui_font(10),
            background=theme.CERAMIC,
            foreground=theme.INK,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=10,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.models.pack(fill=tk.BOTH, expand=True)
        self.models.tag_configure("heading", foreground=theme.INK_SOFT, font=theme.ui_font(9, bold=True))
        self.models.tag_configure("name", foreground=theme.INK, font=theme.ui_font(10))
        self.models.tag_configure("muted", foreground=theme.INK_SOFT, font=theme.ui_font(9))
        self.models.tag_configure("note", foreground=theme.ACCENT, font=theme.ui_font(9))
        self._write_models_idle()

    def _build_output(self, parent) -> None:
        self.output = tk.Text(
            parent,
            wrap=tk.WORD,
            font=theme.mono_font(10),
            background=theme.CERAMIC,
            foreground=theme.INK,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=14,
            pady=10,
            spacing3=2,
            state=tk.DISABLED,
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.tag_configure("ok", foreground=theme.OK)
        self.output.tag_configure("conceptual", foreground=theme.CONCEPTUAL)
        self.output.tag_configure("conceptual_title", foreground=theme.CONCEPTUAL, font=theme.mono_font(10, bold=True))
        self.output.tag_configure("system", foreground=theme.SYSTEM)
        self.output.tag_configure("system_title", foreground=theme.SYSTEM, font=theme.mono_font(10, bold=True))
        self.output.tag_configure("fail", foreground=theme.CONCEPTUAL)
        self.output.tag_configure("title", foreground=theme.CONCEPTUAL, font=theme.mono_font(10, bold=True))
        self.output.tag_configure("muted", foreground=theme.INK_SOFT)
        self._set_output(
            "Ready.\n\nWrite a Ranvier program, then Run.\nAxon will compile the model. It will not open a biological interface.",
            "muted",
        )

    def _build_status(self) -> None:
        self._status_bar = tk.Frame(self.root, bg=theme.DESK, highlightthickness=0)
        self._status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 6))
        self.status = tk.Label(
            self._status_bar,
            text=PHILOSOPHY,
            bg=theme.DESK,
            fg=theme.INK_FAINT,
            font=theme.ui_font(9),
            anchor="w",
        )
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.safety = tk.Label(
            self._status_bar,
            text=theme.SAFETY_LABELS[0],
            bg=theme.DESK,
            fg=theme.ACCENT,
            font=theme.ui_font(9),
            anchor="e",
        )
        self.safety.pack(side=tk.RIGHT, padx=(8, 8))

    def _raise_chrome(self) -> None:
        self._desk.tk.call("lower", self._desk._w)
        self._status_bar.tk.call("raise", self._status_bar._w)

    def _tick_safety(self) -> None:
        labels = theme.SAFETY_LABELS
        self.safety.config(text=labels[self._safety_index % len(labels)])
        self._safety_index = (self._safety_index + 1) % len(labels)
        self.root.after(8000, self._tick_safety)

    def _hide_pane(self, name: str) -> None:
        self._pane_vars[name].set(False)
        self._sync_panes()

    def _toggle_pane(self, name: str) -> None:
        self._pane_vars[name].set(not self._pane_vars[name].get())
        self._sync_panes()

    def _sync_panes(self) -> None:
        columns = {
            "project": (self.project_tablet, 1),
            "editor": (self.editor_tablet, 4),
            "models": (self.model_tablet, 2),
        }
        visible = [key for key in ("project", "editor", "models") if self._pane_vars[key].get()]
        if not visible:
            self._pane_vars["editor"].set(True)
            visible = ["editor"]

        for pane in list(self.columns.panes()):
            self.columns.forget(pane)
        for key in ("project", "editor", "models"):
            if key in visible:
                widget, weight = columns[key]
                self.columns.add(widget, weight=weight)

        output_id = str(self.output_tablet)
        present = output_id in self.outer.panes()
        if self._pane_vars["output"].get() and not present:
            self.outer.add(self.output_tablet, weight=2)
        elif not self._pane_vars["output"].get() and present:
            self.outer.forget(self.output_tablet)
        self._raise_chrome()

    def _title(self) -> str:
        name = self.path.name if self.path else UNTITLED
        dirty = " ·" if self._dirty else ""
        return f"{name}{dirty}  -  {APP_NAME} {APP_VERSION}"

    def _apply_icon(self) -> None:
        self.root.update_idletasks()
        if sys.platform != "win32":
            if TITLEBAR_ICON_PATH.is_file():
                try:
                    self.root.iconbitmap(str(TITLEBAR_ICON_PATH))
                except tk.TclError:
                    pass
            if APP_ICON_PNG.is_file():
                try:
                    photo = tk.PhotoImage(file=str(APP_ICON_PNG))
                    width = int(photo.width())
                    if width > 256:
                        photo = photo.subsample(max(1, round(width / 256)))
                    self._app_icon_photo = photo
                    self.root.iconphoto(True, photo)
                except tk.TclError:
                    pass
            return
        self._prepare_windows_icons()
        self._stamp_windows_icons()
        self.root.after_idle(self._stamp_windows_icons)
        self.root.after(250, self._stamp_windows_icons)

    def _prepare_windows_icons(self) -> None:
        small, big = _window_icon_sizes()
        identity = _app_identity_ico()
        if identity is not None:
            self._hicon_app = _hicon_from_ico(identity, big)
        elif APP_ICON_PNG.is_file():
            self._hicon_app = _hicon_from_png(APP_ICON_PNG, big)
        if TITLEBAR_ICON_PATH.is_file():
            self._hicon_title = _hicon_from_ico(TITLEBAR_ICON_PATH, small)
        self._identity_keep = _set_window_app_id(self.root, identity)

    def _stamp_windows_icons(self) -> None:
        self.root.update_idletasks()
        identity = _app_identity_ico()
        if identity is not None:
            self._identity_keep = _set_window_app_id(self.root, identity)
        if self._hicon_title:
            _windows_set_hicon(self.root, self._hicon_title, big=False)
        if self._hicon_app:
            _windows_set_hicon(self.root, self._hicon_app, big=True)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.root.title(self._title())

    def _on_modified(self, _event=None) -> None:
        if self.text.edit_modified():
            self._set_dirty(True)
            self.text.edit_modified(False)

    def _schedule_highlight(self, _event=None) -> None:
        if self._highlight_job:
            self.root.after_cancel(self._highlight_job)
        self._highlight_job = self.root.after(90, self._refresh_highlight)

    def _refresh_highlight(self) -> None:
        self._highlight_job = None
        syntax.highlight(self.text)
        self._refresh_line_numbers()
        self._refresh_model_panel()

    def _refresh_line_numbers(self) -> None:
        count = int(self.text.index("end-1c").split(".")[0])
        numbers = "\n".join(str(i) for i in range(1, count + 1))
        self.linenumbers.config(state=tk.NORMAL)
        self.linenumbers.delete("1.0", tk.END)
        self.linenumbers.insert("1.0", numbers)
        self.linenumbers.config(state=tk.DISABLED)
        self.linenumbers.yview_moveto(self.text.yview()[0])

    def _on_text_scroll(self, first, last, scrollbar) -> None:
        scrollbar.set(first, last)
        self.linenumbers.yview_moveto(first)

    def _on_scrollbar(self, *args) -> None:
        self.text.yview(*args)
        self.linenumbers.yview(*args)

    def _refresh_project(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._project_nodes.clear()
        programs = self.tree.insert("", "end", text="Programs", open=True)
        models = self.tree.insert("", "end", text="Models", open=True)
        reports = self.tree.insert("", "end", text="Reports", open=True)

        seen: set[Path] = set()
        if EXAMPLES_DIR.exists():
            for path in sorted(EXAMPLES_DIR.glob("*.cog")):
                self._add_project_item(programs, "cog", path)
                seen.add(path.resolve())
        if self.path and self.path.suffix.lower() == DEFAULT_EXT and self.path.exists():
            if self.path.resolve() not in seen:
                self._add_project_item(programs, "cog", self.path)

        if MODELS_DIR.exists():
            for name in MODEL_FILES.values():
                path = MODELS_DIR / name
                if path.exists():
                    self._add_project_item(models, "model", path)

        report_files = sorted(REPORTS_DIR.glob("*")) if REPORTS_DIR.exists() else []
        report_files = [path for path in report_files if path.is_file()]
        if report_files:
            for path in report_files:
                self._add_project_item(reports, "report", path)
        else:
            empty = self.tree.insert(reports, "end", text="(none yet)")
            self._project_nodes[empty] = ("empty", None)

    def _add_project_item(self, parent: str, kind: str, path: Path) -> None:
        item = self.tree.insert(parent, "end", text=path.name)
        self._project_nodes[item] = (kind, path)

    def _on_project_select(self, _event=None) -> None:
        kind, path = self._project_nodes.get(self.tree.focus(), ("", None))
        if kind == "model" and path is not None:
            self._show_model_file(path)

    def _on_project_open(self, _event=None) -> None:
        kind, path = self._project_nodes.get(self.tree.focus(), ("", None))
        if kind == "cog" and path is not None:
            if self._dirty and not self._confirm_discard():
                return
            self._open_path(path)
        elif kind == "report" and path is not None:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                messagebox.showerror(APP_NAME, f"Could not read report:\n{exc}")
                return
            tag = "ok" if "Simulation completed" in text else "fail"
            self._set_output(text, tag)

    def _show_model_file(self, path: Path) -> None:
        role = MODEL_ROLES.get(path.name, "model file")
        self._set_models(
            [
                ("heading", "Selected model\n"),
                ("name", f"{path.name}\n"),
                ("muted", f"{role}\n\n"),
                ("note", "This is a representation, not a brain.\n"),
                ("muted", "Functions, if present, are network processes.\nThey are not single regions."),
            ]
        )

    def _refresh_model_panel(self) -> None:
        source = self.text.get("1.0", "end-1c")
        filename = str(self.path) if self.path else UNTITLED
        try:
            program = parse(source, filename=filename)
        except (CognitionError, ParseError):
            return
        loaded: list[str] = []
        associations: list[tuple[str, str]] = []
        for stmt in program.statements:
            if isinstance(stmt, LoadStmt):
                name = MODEL_ALIASES.get(stmt.model.lower())
                if name and name not in loaded:
                    loaded.append(name)
            elif isinstance(stmt, AssociateStmt):
                associations.append((stmt.function, stmt.network))
        parts: list[tuple[str, str]] = [("heading", "Loaded models\n")]
        if loaded:
            for name in loaded:
                role = MODEL_ROLES.get(name, "")
                parts.append(("name", f"{name}\n"))
                parts.append(("muted", f"  {role}\n"))
        else:
            parts.append(("muted", "None referenced yet.\nUse  load atlas\n"))
        parts.append(("heading", "\nRelationships\n"))
        if associations:
            for function, network in associations:
                parts.append(("name", f"{function}  ->  {network}\n"))
            parts.append(("muted", "\n"))
        else:
            parts.append(("muted", "No associations yet.\nassociate function with network\n\n"))
        parts.append(("note", "Functions are network processes,\nnot single regions."))
        self._set_models(parts)

    def _write_models_idle(self) -> None:
        self._set_models(
            [
                ("heading", "Loaded models\n"),
                ("muted", "Open or write a program.\nAxon will list the models it references.\n\n"),
                ("note", "Functions are network processes,\nnot single regions."),
            ]
        )

    def _set_models(self, parts: list[tuple[str, str]]) -> None:
        self.models.config(state=tk.NORMAL)
        self.models.delete("1.0", tk.END)
        for tag, text in parts:
            self.models.insert(tk.END, text, tag)
        self.models.config(state=tk.DISABLED)

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = messagebox.askyesnocancel(
            APP_NAME,
            "Save this notebook page before leaving it?",
        )
        if answer is None:
            return False
        if answer:
            return self.save_file()
        return True

    def new_file(self) -> None:
        if not self._confirm_discard():
            return
        self._new_buffer(clear_to_template=True)

    def _new_buffer(self, clear_to_template: bool = False) -> None:
        self.path = None
        self.text.delete("1.0", tk.END)
        if clear_to_template:
            self.text.insert("1.0", new_file_template())
        syntax.clear_error_lines(self.text)
        self._refresh_highlight()
        self.text.edit_modified(False)
        self._set_dirty(False)
        self._set_output("New page.\nNothing has been compiled.", "muted")
        self.status.config(text=PHILOSOPHY)

    def open_file(self) -> None:
        if not self._confirm_discard():
            return
        initial = EXAMPLES_DIR if EXAMPLES_DIR.exists() else PROJECT_ROOT
        chosen = filedialog.askopenfilename(
            title="Open Ranvier program",
            initialdir=str(initial),
            filetypes=FILE_TYPES,
            defaultextension=DEFAULT_EXT,
        )
        if chosen:
            self._open_path(Path(chosen))

    def _open_path(self, path: Path) -> None:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not open file:\n{exc}")
            return
        self.path = path
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", source)
        syntax.clear_error_lines(self.text)
        self._refresh_highlight()
        self.text.edit_modified(False)
        self._set_dirty(False)
        self._set_output(f"Opened {path.name}\n", "muted")
        self.status.config(text=str(path))
        self._refresh_project()

    def save_file(self) -> bool:
        if self.path is None:
            return self.save_file_as()
        return self._write_path(self.path)

    def save_file_as(self) -> bool:
        initial = self.path.parent if self.path else (EXAMPLES_DIR if EXAMPLES_DIR.exists() else PROJECT_ROOT)
        name = self.path.name if self.path else UNTITLED
        chosen = filedialog.asksaveasfilename(
            title="Save Ranvier program",
            initialdir=str(initial),
            initialfile=name,
            filetypes=FILE_TYPES,
            defaultextension=DEFAULT_EXT,
        )
        if not chosen:
            return False
        path = Path(chosen)
        if path.suffix.lower() != DEFAULT_EXT:
            path = path.with_suffix(DEFAULT_EXT)
        return self._write_path(path)

    def _write_path(self, path: Path) -> bool:
        try:
            path.write_text(self.text.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not save file:\n{exc}")
            return False
        self.path = path
        self.text.edit_modified(False)
        self._set_dirty(False)
        self.status.config(text=f"Saved {path.name}")
        self._refresh_project()
        return True

    def run_file(self) -> None:
        if self.path is None or self._dirty:
            if not self.save_file():
                return
        assert self.path is not None
        result = runner.run_cog_file(self.path)
        syntax.clear_error_lines(self.text)
        self._refresh_model_panel()
        if result.ok:
            summary = (
                "Simulation completed.\n"
                "No biological interface detected.\n"
                "0 prophecies compiled.\n\n"
                + result.report
            )
            self._set_output(summary, "ok")
            self.status.config(text="Simulation completed. 0 prophecies compiled.")
            self._save_report(self.path, result.report)
            self._refresh_project()
            return
        lines = [err.line for err in result.errors if err.line]
        syntax.mark_error_lines(self.text, lines)
        self._set_output(diagnostics.format_diagnostics(result.errors), "fail")
        self.status.config(text="Compilation paused. A measurement is not an identity.")
        if result.errors and result.errors[0].line:
            self.text.mark_set(tk.INSERT, f"{result.errors[0].line}.0")
            self.text.see(tk.INSERT)

    def _save_report(self, source: Path, report: str) -> None:
        try:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORTS_DIR / f"{source.stem}.report.txt"
            path.write_text(report, encoding="utf-8")
        except OSError:
            return

    def show_viewer_placeholder(self) -> None:
        messagebox.showinfo(viewer.PLACEHOLDER_TITLE, viewer.open_viewer(self.root))

    def show_about(self) -> None:
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} {APP_VERSION}\nRanvier notebook\n\n"
            "Named for the node of Ranvier on a neuron's axon —\n"
            "where a signal is renewed, not assumed.\n\n"
            "A quiet development environment for a fictional language.\n"
            "Advanced because it is careful - not because it glows.\n\n"
            "Axon is not a brain interface.\n"
            "It models representations. It does not control minds.\n\n"
            f"{PHILOSOPHY}",
        )

    def quit(self) -> None:
        if not self._confirm_discard():
            return
        self.root.destroy()

    def _set_output(self, text: str, tag: str) -> None:
        self.output.config(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        if tag != "fail":
            self.output.insert("1.0", text, tag)
        else:
            for index, card in enumerate(text.split("\n\n")):
                if index:
                    self.output.insert(tk.END, "\n\n")
                first, _, rest = card.partition("\n")
                kind = _diagnostic_kind(first)
                if first.endswith("Error"):
                    self.output.insert(tk.END, first, f"{kind}_title")
                    if rest:
                        self.output.insert(tk.END, "\n" + rest, kind)
                else:
                    self.output.insert(tk.END, card, kind)
        self.output.config(state=tk.DISABLED)


def _diagnostic_kind(title: str) -> str:
    name = title.strip()
    if name in theme.SYSTEM_ERRORS:
        return "system"
    return "conceptual"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else None
    _prefer_dpi()
    _claim_windows_identity()
    root = tk.Tk()
    AxonEditor(root, path=path)
    root.mainloop()
    return 0
