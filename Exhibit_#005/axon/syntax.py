"""Axon syntax highlighting for Ranvier (.cog) source.

Colours are quiet on purpose. The whole Ranvier label family
shares one keyword colour so the page stays calm.
"""

from __future__ import annotations

import tkinter as tk
from typing import Iterable

from . import theme

LANGUAGE_KEYWORDS = (
    "REGION",
    "STRUCTURE",
    "TRACT",
    "NETWORK",
    "CONNECTION",
    "FUNCTION",
    "PROCESS",
    "SIGNAL",
    "TEMP",
    "STATE",
    "PATTERN",
    "PREDICTION",
    "ID",
)
FORBIDDEN_LABELS = ("DESTINY", "PERSONALITY", "FATE")
VERBS = (
    "load",
    "associate",
    "connect",
    "measure",
    "observe",
    "predict",
    "lookup",
)
PARTICLES = ("with", "to", "via", "of", "as", "from")


def configure_tags(widget: tk.Text, font_bold) -> None:
    widget.tag_configure("keyword", foreground=theme.KEYWORD, font=font_bold)
    widget.tag_configure("forbidden", foreground=theme.FORBIDDEN, font=font_bold)
    widget.tag_configure("verb", foreground=theme.VERB)
    widget.tag_configure("particle", foreground=theme.INK_SOFT)
    widget.tag_configure("comment", foreground=theme.COMMENT)
    widget.tag_configure("string", foreground=theme.STRING)
    widget.tag_configure("errorline", background=theme.ERROR_LINE)


def highlight(widget: tk.Text) -> None:
    for tag in (
        "keyword",
        "forbidden",
        "verb",
        "particle",
        "comment",
        "string",
    ):
        widget.tag_remove(tag, "1.0", "end")

    source = widget.get("1.0", "end-1c")
    if not source:
        return

    for line_no, line in enumerate(source.splitlines(), start=1):
        _highlight_line(widget, line_no, line)


def mark_error_lines(widget: tk.Text, lines: Iterable[int]) -> None:
    widget.tag_remove("errorline", "1.0", "end")
    for line in lines:
        if line is None or line < 1:
            continue
        widget.tag_add("errorline", f"{line}.0", f"{line}.end+1c")


def clear_error_lines(widget: tk.Text) -> None:
    widget.tag_remove("errorline", "1.0", "end")


def _highlight_line(widget: tk.Text, line_no: int, line: str) -> None:
    comment_at = _comment_index(line)
    code = line if comment_at is None else line[:comment_at]
    if comment_at is not None:
        widget.tag_add("comment", f"{line_no}.{comment_at}", f"{line_no}.end")

    _tag_strings(widget, line_no, code)
    _tag_words(widget, line_no, code, LANGUAGE_KEYWORDS, "keyword")
    _tag_words(widget, line_no, code, FORBIDDEN_LABELS, "forbidden")
    _tag_words(widget, line_no, code, VERBS, "verb", ignore_case=True)
    _tag_words(widget, line_no, code, PARTICLES, "particle", ignore_case=True)


def _comment_index(line: str) -> int | None:
    in_single = False
    in_double = False
    for i, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return i
    return None


def _tag_strings(widget: tk.Text, line_no: int, code: str) -> None:
    i = 0
    while i < len(code):
        if code[i] in "\"'":
            quote = code[i]
            j = i + 1
            while j < len(code) and code[j] != quote:
                j += 1
            end = j + 1 if j < len(code) else len(code)
            widget.tag_add("string", f"{line_no}.{i}", f"{line_no}.{end}")
            i = end
        else:
            i += 1


def _tag_words(
    widget: tk.Text,
    line_no: int,
    code: str,
    words: Iterable[str],
    tag: str,
    ignore_case: bool = False,
) -> None:
    table = {w.lower() if ignore_case else w: w for w in words}
    i = 0
    length = len(code)
    while i < length:
        if code[i].isalnum() or code[i] == "_":
            j = i
            while j < length and (code[j].isalnum() or code[j] == "_"):
                j += 1
            token = code[i:j]
            key = token.lower() if ignore_case else token
            if key in table:
                widget.tag_add(tag, f"{line_no}.{i}", f"{line_no}.{j}")
            i = j
        else:
            i += 1
