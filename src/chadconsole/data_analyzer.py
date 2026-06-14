"""
chadconsole.data_analyzer
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inspects raw print() arguments, detects their types, formats structured
data with pprint, and returns tagged Payload objects for the UI layer.

Tags:
    "standard"      — plain text (str, int, float, bool, etc.)
    "list"          — a list object
    "dictionary"    — a dict object
    "tuple"         — a tuple object
    "loop_pattern"  — multiple lines from a loop (grouped by core_interceptor)
    "input"         — signals the UI to show an entry field (InputRequest)
    "error"         — unhandled exception (ErrorPayload)
"""

from __future__ import annotations

import pprint
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Payload — the single data unit that flows through the queue
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Payload:
    """A tagged chunk of output destined for the UI."""

    tag: str        # "standard" | "list" | "dictionary" | "tuple" | "loop_pattern"
    content: str    # The formatted string to display


@dataclass(slots=True)
class InputRequest:
    """Signals the UI to show an input entry field."""

    prompt: str
    handler: Any = None


@dataclass(slots=True)
class ErrorPayload:
    """Signals the UI to display a red error block for an unhandled exception."""

    error_type: str          # e.g. "NameError", "ZeroDivisionError", "SyntaxError"
    message: str             # str(exception) — the short human-readable message
    traceback: str = ""      # Full formatted traceback (empty for simple stderr errors)


# ---------------------------------------------------------------------------
# Tag mapping — structural types only
# ---------------------------------------------------------------------------

_TYPE_TAG_MAP: dict[type, str] = {
    list:  "list",
    dict:  "dictionary",
    tuple: "tuple",
}

_PRETTY_PRINTER = pprint.PrettyPrinter(indent=2, width=80, sort_dicts=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(*args: Any, sep: str = " ") -> Payload:
    """Inspect raw print() arguments and return a tagged Payload.

    Strategy:
    - Exactly ONE argument that is a list, dict, or tuple → structured tag + pformat.
    - Everything else → join with *sep* and tag as "standard".

    Note: loop detection is handled upstream in core_interceptor, NOT here.
    This function is purely about *what* is being printed, not *how many times*.
    """
    if len(args) == 1:
        obj = args[0]
        tag = _TYPE_TAG_MAP.get(type(obj))
        if tag is not None:
            content = _PRETTY_PRINTER.pformat(obj)
            return Payload(tag=tag, content=content)

    # Fallback: join everything as plain text
    content = sep.join(str(a) for a in args)
    return Payload(tag="standard", content=content)
