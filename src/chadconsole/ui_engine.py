"""
chadconsole.ui_engine
~~~~~~~~~~~~~~~~~~~~~

Main CustomTkinter window with queue-driven rendering loop.
Polls the shared queue every 50ms and instantiates the appropriate
ui_components widget based on the payload tag.
"""

from __future__ import annotations

import queue
import sys
import traceback
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

import customtkinter as ctk

from chadconsole.data_analyzer import ErrorPayload, InputRequest, Payload
from chadconsole.ui_components import (
    Colors,
    ErrorBlock,
    FONT_BODY,
    FONT_HEADER,
    FONT_LABEL,
    FONT_TITLE,
    InputBlock,
    LoopPatternBlock,
    StandardBlock,
    StructuredBlock,
)

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
_ASSETS_DIR = Path(__file__).parent / "assets"
_LOGO_PATH = _ASSETS_DIR / "logo.png"


# ---------------------------------------------------------------------------
# Tag → Component mapping
# ---------------------------------------------------------------------------

_TAG_WIDGET_MAP = {
    "standard":     StandardBlock,
    "list":         StructuredBlock,
    "dictionary":   StructuredBlock,
    "tuple":        StructuredBlock,
    "loop_pattern": LoopPatternBlock,
}

# Original stderr for error logging (never intercepted)
_stderr = sys.__stderr__


# ---------------------------------------------------------------------------
# PrettyConsoleApp — The Main Window
# ---------------------------------------------------------------------------

class PrettyConsoleApp(ctk.CTk):
    """Premium dark-mode console window.

    Continuously polls a thread-safe queue and renders payloads as
    visual blocks in a scrollable canvas.
    """

    POLL_INTERVAL_MS = 50   # ~20 fps
    MAX_DRAIN = 10          # Max items per poll tick

    def __init__(self, output_queue: queue.Queue) -> None:
        super().__init__()

        self._queue = output_queue
        self._input_handler = None  # Set later via set_input_handler()
        self._closed = False

        # ── Window configuration ──────────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("✦ ChadConsole")
        self.geometry("780x500")
        self.minsize(520, 400)
        self.configure(fg_color=Colors.BG_MAIN)

        # ── Header bar ────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, height=60, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # App icon + title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=10)

        # Try to load premium logo image, fallback to text icon if not found
        icon_label = None
        if _LOGO_PATH.exists():
            try:
                pil_img = Image.open(_LOGO_PATH)
                logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
                icon_label = ctk.CTkLabel(
                    title_frame,
                    image=logo_img,
                    text="",
                )
            except Exception:
                pass

        if icon_label is None:
            icon_label = ctk.CTkLabel(
                title_frame,
                text="✦",
                font=("Inter", 22),
                text_color=Colors.ACCENT_BLUE,
            )
        icon_label.pack(side="left", padx=(0, 8))

        title_label = ctk.CTkLabel(
            title_frame,
            text="ChadConsole",
            font=FONT_TITLE,
            text_color=Colors.TEXT_PRIMARY,
        )
        title_label.pack(side="left")

        # Subtle version badge
        version_badge = ctk.CTkLabel(
            header,
            text="v0.1.0",
            font=FONT_LABEL,
            text_color=Colors.TEXT_DIM,
        )
        version_badge.pack(side="right", padx=20)

        # ── Separator line ────────────────────────────────────────────


        # ── Scrollable content area ───────────────────────────────────
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=Colors.BG_MAIN,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER_SUBTLE,
            scrollbar_button_hover_color=Colors.TEXT_DIM,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Status bar ────────────────────────────────────────────────
        self._status_bar = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, height=30, corner_radius=0)
        self._status_bar.pack(fill="x", side="bottom")
        self._status_bar.pack_propagate(False)

        self._status_label = ctk.CTkLabel(
            self._status_bar,
            text="● Connected",
            font=FONT_LABEL,
            text_color=Colors.ACCENT_GREEN,
        )
        self._status_label.pack(side="left", padx=16, pady=4)

        self._block_count = 0
        self._count_label = ctk.CTkLabel(
            self._status_bar,
            text="0 blocks",
            font=FONT_LABEL,
            text_color=Colors.TEXT_SECONDARY,
        )
        self._count_label.pack(side="right", padx=16, pady=4)

        # ── Lifecycle ─────────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start the rendering loop
        self.after(self.POLL_INTERVAL_MS, self._poll_queue)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_input_handler(self, handler) -> None:
        """Wire the input handler so InputBlock can resolve responses."""
        self._input_handler = handler

    # ------------------------------------------------------------------
    # Queue polling & rendering
    # ------------------------------------------------------------------

    def _poll_queue(self) -> None:
        """Drain up to MAX_DRAIN items from the queue and render them."""
        if self._closed:
            return

        try:
            items_processed = 0
            while items_processed < self.MAX_DRAIN:
                try:
                    item = self._queue.get_nowait()
                except queue.Empty:
                    break

                self._render_item(item)
                items_processed += 1
        except Exception:
            _stderr.write(f"[ChadConsole] poll error:\n{traceback.format_exc()}\n")

        # Always schedule next poll (even after errors)
        if not self._closed:
            self.after(self.POLL_INTERVAL_MS, self._poll_queue)

    def _render_item(self, item) -> None:
        """Instantiate the correct widget for a queue item."""
        try:
            if isinstance(item, InputRequest):
                self._render_input(item)
            elif isinstance(item, ErrorPayload):
                self._render_error(item)
            elif isinstance(item, Payload):
                self._render_payload(item)
        except Exception:
            _stderr.write(f"[ChadConsole] render error:\n{traceback.format_exc()}\n")

    def _render_payload(self, payload: Payload) -> None:
        """Render a tagged Payload as the appropriate visual block."""
        widget_cls = _TAG_WIDGET_MAP.get(payload.tag, StandardBlock)

        if widget_cls is StructuredBlock:
            widget = widget_cls(
                self._scroll_frame,
                text=payload.content,
                data_type=payload.tag,
            )
        else:
            widget = widget_cls(
                self._scroll_frame,
                text=payload.content,
            )

        widget.pack()
        self._block_count += 1
        self._count_label.configure(text=f"{self._block_count} blocks")

        # Auto-scroll to bottom
        self._scroll_to_bottom()

    def _render_input(self, req: InputRequest) -> None:
        """Render an InputBlock and wire its submit callback."""
        handler = req.handler or self._input_handler

        def on_submit(value: str) -> None:
            if handler:
                handler.resolve(value)
            self._block_count += 1
            self._count_label.configure(text=f"{self._block_count} blocks")

        widget = InputBlock(
            self._scroll_frame,
            prompt=req.prompt,
            on_submit=on_submit,
        )
        widget.pack()

        # Auto-scroll to bottom
        self._scroll_to_bottom()

    def _render_error(self, err: ErrorPayload) -> None:
        """Render an ErrorBlock for an unhandled exception."""
        widget = ErrorBlock(
            self._scroll_frame,
            error_type=err.error_type,
            message=err.message,
            traceback=err.traceback,
        )
        widget.pack()
        self._block_count += 1
        self._count_label.configure(text=f"{self._block_count} blocks")
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        """Schedule a scroll-to-bottom after the widget is rendered."""
        def _do_scroll():
            try:
                self._scroll_frame._parent_canvas.yview_moveto(1.0)
            except Exception:
                pass  # Graceful fallback if internal API changes
        self.after(30, _do_scroll)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        """Handle window close — restore originals and destroy."""
        self._closed = True
        from chadconsole.core_interceptor import uninstall
        uninstall()

        self._status_label.configure(text="● Disconnected", text_color=Colors.TEXT_DIM)
        self.after(100, self.destroy)
