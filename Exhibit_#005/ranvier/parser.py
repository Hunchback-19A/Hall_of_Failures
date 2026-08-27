"""Line-oriented parser for Ranvier (.cog) source.

The syntax is intentionally small and Python-like:

    REGION frontal_lobe
    FUNCTION decision_making
    associate decision_making with decision_network
    PREDICTION success_probability = learning_trend

    Ranvier is not trying to be a general-purpose language. It is a safety
layer for brain-related *representations*.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .errors import CognitionError, CognitionValueError
from .labels import LABELS


@dataclass(frozen=True)
class Span:
    filename: str
    line: int
    column: int
    text: str


@dataclass(frozen=True)
class NameExpr:
    name: str
    span: Span


@dataclass(frozen=True)
class SubscriptExpr:
    name: str
    key: str
    span: Span


Expr = Union[NameExpr, SubscriptExpr]


@dataclass
class LoadStmt:
    model: str
    span: Span


@dataclass
class Declaration:
    label: str
    name: str
    value: Optional[Expr]
    span: Span


@dataclass
class Assignment:
    name: str
    value: Expr
    span: Span


@dataclass
class AssociateStmt:
    function: str
    network: str
    span: Span


@dataclass
class ConnectStmt:
    source: str
    target: str
    tract: str
    span: Span


@dataclass
class MeasureStmt:
    state: str
    of: str
    span: Span


@dataclass
class ObserveStmt:
    behavior: str
    as_name: str
    span: Span


@dataclass
class PredictStmt:
    prediction: str
    source: str
    span: Span


@dataclass
class LookupStmt:
    expr: Expr
    span: Span


Stmt = Union[
    LoadStmt,
    Declaration,
    Assignment,
    AssociateStmt,
    ConnectStmt,
    MeasureStmt,
    ObserveStmt,
    PredictStmt,
    LookupStmt,
]


@dataclass
class Program:
    filename: str
    source_lines: list[str]
    statements: list[Stmt]


class ParseError(CognitionError):
    """Printed as SyntaxError."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.error_type = "SyntaxError"


def parse_file(path: str) -> Program:
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return parse(source, filename=path)


def parse(source: str, filename: str = "<memory>") -> Program:
    lines = source.splitlines()
    statements: list[Stmt] = []
    for index, raw in enumerate(lines, start=1):
        stripped = _strip_comment(raw).strip()
        if not stripped:
            continue
        span = Span(filename=filename, line=index, column=_first_nonspace(raw) + 1, text=raw.rstrip("\n"))
        statements.append(_parse_line(stripped, span))
    return Program(filename=filename, source_lines=lines, statements=statements)


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    chars: list[str] = []
    for char in line:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        chars.append(char)
    return "".join(chars)


def _first_nonspace(line: str) -> int:
    for i, char in enumerate(line):
        if not char.isspace():
            return i
    return 0


def _parse_line(text: str, span: Span) -> Stmt:
    tokens = _tokenize(text)
    if not tokens:
        raise ParseError("Empty statement.", filename=span.filename, line=span.line, column=span.column, source_line=span.text)

    head = tokens[0].upper()

    if head == "LOAD":
        _expect_len(tokens, 2, span, "load <model>")
        return LoadStmt(model=tokens[1].lower(), span=span)

    if head == "ASSOCIATE":
        _expect_keyword(tokens, 2, "with", span, "associate <function> with <network>")
        _expect_len(tokens, 4, span, "associate <function> with <network>")
        return AssociateStmt(function=tokens[1], network=tokens[3], span=span)

    if head == "CONNECT":
        _expect_keyword(tokens, 2, "to", span, "connect <region> to <region> via <tract>")
        _expect_keyword(tokens, 4, "via", span, "connect <region> to <region> via <tract>")
        _expect_len(tokens, 6, span, "connect <region> to <region> via <tract>")
        return ConnectStmt(source=tokens[1], target=tokens[3], tract=tokens[5], span=span)

    if head == "MEASURE":
        _expect_keyword(tokens, 2, "of", span, "measure <state> of <network_or_region>")
        _expect_len(tokens, 4, span, "measure <state> of <network_or_region>")
        return MeasureStmt(state=tokens[1], of=tokens[3], span=span)

    if head == "OBSERVE":
        _expect_keyword(tokens, 2, "as", span, "observe <behavior> as <state_or_pattern>")
        _expect_len(tokens, 4, span, "observe <behavior> as <state_or_pattern>")
        return ObserveStmt(behavior=tokens[1], as_name=tokens[3], span=span)

    if head == "PREDICT":
        _expect_keyword(tokens, 2, "from", span, "predict <prediction> from <state_or_pattern>")
        _expect_len(tokens, 4, span, "predict <prediction> from <state_or_pattern>")
        return PredictStmt(prediction=tokens[1], source=tokens[3], span=span)

    if head == "LOOKUP":
        rest = text.split(None, 1)
        if len(rest) < 2:
            raise ParseError(
                "lookup requires a name or subscript.",
                filename=span.filename,
                line=span.line,
                column=span.column,
                source_line=span.text,
                hint="lookup frontal_lobe  or  lookup frontal_lobe[\"centroid\"]",
            )
        return LookupStmt(expr=_parse_expr(rest[1], span), span=span)

    if "=" in tokens:
        return _parse_assignment(text, tokens, span)

    if head in LABELS:
        _expect_len(tokens, 2, span, f"{head} <name>")
        return Declaration(label=head, name=tokens[1], value=None, span=span)

    raise ParseError(
        f"Unknown statement {text!r}.",
        filename=span.filename,
        line=span.line,
        column=span.column,
        source_line=span.text,
        hint="a label declaration (REGION name), associate, connect, measure, observe, predict, lookup, or load",
    )


def _parse_assignment(text: str, tokens: list[str], span: Span) -> Stmt:
    left, right = _split_assign(text)
    left_tokens = _tokenize(left)
    if not left_tokens:
        raise ParseError(
            "Missing assignment target.",
            filename=span.filename,
            line=span.line,
            column=span.column,
            source_line=span.text,
        )
    expr = _parse_expr(right, span)
    if left_tokens[0].upper() in LABELS and len(left_tokens) == 2:
        return Declaration(label=left_tokens[0].upper(), name=left_tokens[1], value=expr, span=span)
    if len(left_tokens) == 1:
        return Assignment(name=left_tokens[0], value=expr, span=span)
    if left_tokens[0].upper() not in LABELS and left_tokens[0].isupper():
        # Unknown ALLCAPS label such as DESTINY or PERSONALITY.
        if len(left_tokens) == 1:
            return Declaration(label=left_tokens[0].upper(), name=left_tokens[0].lower(), value=expr, span=span)
        return Declaration(label=left_tokens[0].upper(), name=left_tokens[1], value=expr, span=span)
    raise ParseError(
        f"Invalid assignment target {left!r}.",
        filename=span.filename,
        line=span.line,
        column=span.column,
        source_line=span.text,
        hint="<name> = <expr>  or  <LABEL> <name> = <expr>",
    )


def _split_assign(text: str) -> tuple[str, str]:
    depth = 0
    in_single = False
    in_double = False
    for i, char in enumerate(text):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "[" and not in_single and not in_double:
            depth += 1
        elif char == "]" and not in_single and not in_double:
            depth -= 1
        elif char == "=" and depth == 0 and not in_single and not in_double:
            return text[:i].strip(), text[i + 1 :].strip()
    raise CognitionValueError("Assignment is missing a right-hand side.")


def _parse_expr(text: str, span: Span) -> Expr:
    text = text.strip()
    if not text:
        raise ParseError(
            "Missing expression.",
            filename=span.filename,
            line=span.line,
            column=span.column,
            source_line=span.text,
        )
    if "[" in text:
        name, rest = text.split("[", 1)
        name = name.strip()
        if not rest.endswith("]"):
            raise ParseError(
                "Unclosed coordinate subscript.",
                filename=span.filename,
                line=span.line,
                column=span.column,
                source_line=span.text,
                hint='brain_region["centroid"]',
            )
        key = rest[:-1].strip().strip("\"'")
        if not name:
            raise ParseError(
                "Subscript is missing a region name.",
                filename=span.filename,
                line=span.line,
                column=span.column,
                source_line=span.text,
            )
        return SubscriptExpr(name=name, key=key, span=span)
    tokens = _tokenize(text)
    if len(tokens) != 1:
        raise ParseError(
            f"Invalid expression {text!r}.",
            filename=span.filename,
            line=span.line,
            column=span.column,
            source_line=span.text,
        )
    return NameExpr(name=tokens[0], span=span)


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(text):
        char = text[i]
        if char in " \t" and not in_single and not in_double:
            if current:
                tokens.append("".join(current))
                current = []
            i += 1
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue
        if char in "[]=" and not in_single and not in_double:
            if current:
                tokens.append("".join(current))
                current = []
            tokens.append(char)
            i += 1
            continue
        current.append(char)
        i += 1
    if current:
        tokens.append("".join(current))
    return tokens


def _expect_len(tokens: list[str], length: int, span: Span, form: str) -> None:
    if len(tokens) != length:
        raise ParseError(
            f"Expected `{form}`.",
            filename=span.filename,
            line=span.line,
            column=span.column,
            source_line=span.text,
        )


def _expect_keyword(tokens: list[str], index: int, word: str, span: Span, form: str) -> None:
    if len(tokens) <= index or tokens[index].lower() != word:
        raise ParseError(
            f"Expected `{form}`.",
            filename=span.filename,
            line=span.line,
            column=span.column,
            source_line=span.text,
        )
