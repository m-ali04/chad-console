"""
chadconsole.ui_components
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom CTkFrame-based visual blocks for each output type.
Every component is packed with pady=15 for distinct visual spacing.

Design: Dark neumorphic with deep blue accents and purple loop containers.
"""

from __future__ import annotations

import customtkinter as ctk


# ---------------------------------------------------------------------------
# Color Palette — Dark Neumorphic Blue
# ---------------------------------------------------------------------------

class Colors:
    """Centralized color tokens for the entire UI."""

    BG_MAIN       = "#0D1117"   # Deep dark background
    BG_CARD_NAVBAR = "#0c0e12"   # Card / frame background
    BG_CARD       = "#161B22"   # Card / frame background
    BG_CARD_ALT   = "#1C2333"   # Alternate card — structured data
    BG_LOOP       = "#1A1232"   # Loop container — purple-tinted dark
    BG_INPUT      = "#0F1923"   # Input block background

    ACCENT_BLUE   = "#58A6FF"   # Primary accent — borders, cursor, highlights
    ACCENT_PURPLE = "#8B5CF6"   # Loop container border & accent
    ACCENT_GREEN  = "#3FB950"   # Success / type badges
    ACCENT_AMBER  = "#D29922"   # Warning / tuple badge

    TEXT_PRIMARY   = "#E6EDF3"   # Main text
    TEXT_SECONDARY = "#8B949E"   # Timestamps, labels
    TEXT_MONO      = "#79C0FF"   # Monospace text in loop containers
    TEXT_DIM       = "#484F58"   # Very subtle text

    BORDER_SUBTLE  = "#30363D"   # Subtle card borders
    BORDER_BLUE    = "#1F6FEB"   # Blue accent border
    BORDER_PURPLE  = "#6D28D9"   # Purple accent border (loops)
    BORDER_RED     = "#7B1A1A"   # Error block inner border

    ACCENT_RED     = "#FF6B6B"   # Error accent — badge, left bar
    BG_ERROR       = "#160A0A"   # Error block background (dark blood-red tint)
    TEXT_ERROR     = "#FF8585"   # Error message / traceback text

    INPUT_BG       = "#0D1117"   # Entry field background
    INPUT_BORDER   = "#58A6FF"   # Entry field border


# ---------------------------------------------------------------------------
# Font constants
# ---------------------------------------------------------------------------

FONT_BODY      = ("Inter", 14)
FONT_BODY_BOLD = ("Inter", 14, "bold")
FONT_MONO      = ("Consolas", 13)
FONT_MONO_LG   = ("Consolas", 14)
FONT_BADGE     = ("Inter", 11, "bold")
FONT_LABEL     = ("Inter", 12)
FONT_HEADER    = ("Inter", 16, "bold")
FONT_TITLE     = ("Inter", 16, "bold")


# ---------------------------------------------------------------------------
# Base Block
# ---------------------------------------------------------------------------

class _BaseBlock(ctk.CTkFrame):
    """Base class for all output blocks.

    Provides consistent card styling with a colored left accent border.
    """

    PACK_PADY = 8  # Enforced gap between blocks

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        accent_color: str = Colors.ACCENT_BLUE,
        bg_color: str = Colors.BG_CARD,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=bg_color,
            corner_radius=10,
            border_width=0,
            **kwargs,
        )

        # Outer container with left accent stripe
        self._accent_bar = ctk.CTkFrame(
            self,
            fg_color=accent_color,
            width=4,
            height=0,
            corner_radius=2,
        )
        self._accent_bar.pack(side="left", fill="y", padx=(0, 0), pady=4)

        # Content area
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=False, padx=(12, 16), pady=4)

    def pack(self, **kwargs) -> None:
        """Override pack to enforce the required 15px vertical gap."""
        kwargs.setdefault("pady", self.PACK_PADY)
        kwargs.setdefault("padx", 16)
        kwargs.setdefault("anchor", "w")
        super().pack(**kwargs)


# ---------------------------------------------------------------------------
# StandardBlock — plain text output
# ---------------------------------------------------------------------------

class StandardBlock(_BaseBlock):
    """Renders standard text output in a clean card."""

    def __init__(self, master: ctk.CTkBaseClass, text: str, **kwargs) -> None:
        super().__init__(master, accent_color=Colors.ACCENT_BLUE, bg_color=Colors.BG_CARD, **kwargs)

        label = ctk.CTkLabel(
            self._content,
            text=text,
            font=FONT_BODY,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=600,
        )
        label.pack(fill="x", anchor="w")


# ---------------------------------------------------------------------------
# StructuredBlock — list, dict, tuple
# ---------------------------------------------------------------------------

# Badge colors per type
_BADGE_STYLES: dict[str, tuple[str, str]] = {
    "list":       (Colors.ACCENT_BLUE,  "LIST"),
    "dictionary": (Colors.ACCENT_GREEN, "DICT"),
    "tuple":      (Colors.ACCENT_AMBER, "TUPLE"),
}


class StructuredBlock(_BaseBlock):
    """Renders structured data (list/dict/tuple) with a type badge
    and monospace formatted content.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        text: str,
        data_type: str = "dictionary",
        **kwargs,
    ) -> None:
        badge_color, badge_label = _BADGE_STYLES.get(data_type, (Colors.ACCENT_BLUE, "DATA"))
        super().__init__(master, accent_color=badge_color, bg_color=Colors.BG_CARD_ALT, **kwargs)

        # Type badge
        badge_frame = ctk.CTkFrame(
            self._content,
            fg_color=badge_color,
            corner_radius=6,
            height=22,
        )
        badge_frame.pack(anchor="w", pady=(0, 8))

        badge_text = ctk.CTkLabel(
            badge_frame,
            text=f"  {badge_label}  ",
            font=FONT_BADGE,
            text_color=Colors.BG_MAIN,
            height=22,
        )
        badge_text.pack(padx=2, pady=1)

        # Formatted content in monospace
        content_frame = ctk.CTkFrame(
            self._content,
            fg_color=Colors.BG_CARD,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_SUBTLE,
        )
        content_frame.pack(fill="x", pady=(0, 0))

        content_label = ctk.CTkLabel(
            content_frame,
            text=text,
            font=FONT_MONO,
            text_color=Colors.TEXT_PRIMARY,
            anchor="nw",
            justify="left",
            wraplength=580,
        )
        content_label.pack(fill="x", padx=12, pady=10, anchor="w")


# ---------------------------------------------------------------------------
# LoopPatternBlock — grouped rapid-fire prints
# ---------------------------------------------------------------------------

class LoopPatternBlock(_BaseBlock):
    """Renders grouped loop output in a distinct purple-accented container
    with strict monospace font for perfect ASCII alignment.
    """

    def __init__(self, master: ctk.CTkBaseClass, text: str, **kwargs) -> None:
        super().__init__(
            master,
            accent_color=Colors.ACCENT_PURPLE,
            bg_color=Colors.BG_LOOP,
            **kwargs,
        )

        # Header badge
        header_frame = ctk.CTkFrame(self._content, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 8))

        badge = ctk.CTkFrame(
            header_frame,
            fg_color=Colors.ACCENT_PURPLE,
            corner_radius=6,
            height=22,
        )
        badge.pack(side="left")

        badge_label = ctk.CTkLabel(
            badge,
            text="  LOOP OUTPUT  ",
            font=FONT_BADGE,
            text_color="#FFFFFF",
            height=22,
        )
        badge_label.pack(padx=2, pady=1)

        # Line count indicator
        line_count = text.count("\n") + 1
        count_label = ctk.CTkLabel(
            header_frame,
            text=f"{line_count} lines",
            font=FONT_LABEL,
            text_color=Colors.TEXT_SECONDARY,
        )
        count_label.pack(side="left", padx=(10, 0))

        # Monospace content area
        mono_frame = ctk.CTkFrame(
            self._content,
            fg_color="#0D0D1A",
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_PURPLE,
        )
        mono_frame.pack(fill="x")

        mono_label = ctk.CTkLabel(
            mono_frame,
            text=text,
            font=FONT_MONO_LG,
            text_color=Colors.TEXT_MONO,
            anchor="nw",
            justify="left",
        )
        mono_label.pack(fill="x", padx=14, pady=12, anchor="w")


# ---------------------------------------------------------------------------
# InputBlock — floating input entry field
# ---------------------------------------------------------------------------

class InputBlock(_BaseBlock):
    """Renders an input prompt with an entry field.

    When the user presses Enter, calls the provided callback with the value.
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        prompt: str = "",
        on_submit: callable = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            accent_color=Colors.ACCENT_BLUE,
            bg_color=Colors.BG_INPUT,
            **kwargs,
        )
        self._on_submit = on_submit
        self._submitted = False

        # Prompt label
        if prompt:
            prompt_label = ctk.CTkLabel(
                self._content,
                text=prompt,
                font=FONT_BODY_BOLD,
                text_color=Colors.ACCENT_BLUE,
                anchor="w",
            )
            prompt_label.pack(fill="x", pady=(0, 8))

        # Input row: entry + submit button
        input_row = ctk.CTkFrame(self._content, fg_color="transparent")
        input_row.pack(fill="x")

        self._entry = ctk.CTkEntry(
            input_row,
            font=FONT_MONO,
            fg_color=Colors.INPUT_BG,
            text_color=Colors.TEXT_PRIMARY,
            border_color=Colors.INPUT_BORDER,
            border_width=2,
            corner_radius=8,
            height=40,
            placeholder_text="Type here and press Enter...",
            placeholder_text_color=Colors.TEXT_DIM,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._entry.bind("<Return>", self._handle_submit)

        self._submit_btn = ctk.CTkButton(
            input_row,
            text="Submit",
            font=FONT_BADGE,
            fg_color=Colors.ACCENT_BLUE,
            hover_color=Colors.BORDER_BLUE,
            text_color="#FFFFFF",
            corner_radius=8,
            width=80,
            height=40,
            command=lambda: self._handle_submit(None),
        )
        self._submit_btn.pack(side="right")

        # Auto-focus the entry
        self._entry.after(100, self._entry.focus_set)

    def _handle_submit(self, event) -> None:
        """Handle Enter key or button click."""
        if self._submitted:
            return
        self._submitted = True

        value = self._entry.get()

        # Visual feedback: disable entry, change accent to green
        self._entry.configure(state="disabled", border_color=Colors.ACCENT_GREEN)
        self._submit_btn.configure(state="disabled", fg_color=Colors.BORDER_SUBTLE)
        self._accent_bar.configure(fg_color=Colors.ACCENT_GREEN)

        if self._on_submit:
            self._on_submit(value)


# ---------------------------------------------------------------------------
# ErrorBlock — unhandled exception display
# ---------------------------------------------------------------------------

class ErrorBlock(_BaseBlock):
    """Renders an unhandled exception as a red-accented error card.

    Shows:
    - A red badge with the exception type (e.g. "NameError")
    - The short error message in bold
    - The full traceback in a dark monospace code box (when available)
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        error_type: str,
        message: str,
        traceback: str = "",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            accent_color=Colors.ACCENT_RED,
            bg_color=Colors.BG_ERROR,
            **kwargs,
        )

        # ── Error type badge ───────────────────────────────────────────
        header_row = ctk.CTkFrame(self._content, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 8))

        badge_frame = ctk.CTkFrame(
            header_row,
            fg_color=Colors.ACCENT_RED,
            corner_radius=6,
            height=22,
        )
        badge_frame.pack(side="left")

        badge_text = ctk.CTkLabel(
            badge_frame,
            text=f"  ✕  {error_type}  ",
            font=FONT_BADGE,
            text_color="#FFFFFF",
            height=22,
        )
        badge_text.pack(padx=2, pady=1)

        # ── Error message ──────────────────────────────────────────────
        if message:
            msg_label = ctk.CTkLabel(
                self._content,
                text=message,
                font=FONT_BODY_BOLD,
                text_color=Colors.TEXT_ERROR,
                anchor="w",
                justify="left",
                wraplength=580,
            )
            msg_label.pack(fill="x", pady=(0, 8) if traceback else (0, 2))

        # ── Traceback code box (shown only when traceback is present) ──
        if traceback:
            tb_frame = ctk.CTkFrame(
                self._content,
                fg_color="#0D0404",
                corner_radius=8,
                border_width=1,
                border_color=Colors.BORDER_RED,
            )
            tb_frame.pack(fill="x")

            tb_label = ctk.CTkLabel(
                tb_frame,
                text=traceback,
                font=FONT_MONO,
                text_color=Colors.TEXT_ERROR,
                anchor="nw",
                justify="left",
            )
            tb_label.pack(fill="x", padx=12, pady=10, anchor="w")
