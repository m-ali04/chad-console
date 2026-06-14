"""
chadconsole.core_interceptor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Hijacks sys.stdout, builtins.print, and builtins.input to route all I/O
through a thread-safe queue to the PrettyConsole UI.

Key features:
- ConsoleWriter replaces sys.stdout (captures raw write() calls)
- custom_print replaces builtins.print with structural loop detection
- custom_input replaces builtins.input (blocks caller, signals UI for input field)

Loop Detection Strategy (bytecode-based, no timers needed):
    On each print() call, we inspect the caller's call-stack frames using
    ``dis.get_instructions()`` to check whether the print was called from
    inside a ``for`` loop body.

    For each frame we:
      1. Collect all ``FOR_ITER`` instructions and their loop-end offsets.
      2. Collect all ``JUMP_BACKWARD`` instructions and which ``FOR_ITER`` they
         jump back to.
      3. If the frame's ``f_lasti`` (last executed bytecode offset) falls
         within [FOR_ITER+2 .. JUMP_BACKWARD], we are in a loop body.
      4. Return a key ``(filename, code_id, for_iter_offset)`` that uniquely
         identifies this specific loop.

    Consecutive prints sharing the same key are accumulated into a single
    buffer and emitted as one ``loop_pattern`` payload when the key changes
    or a non-loop print arrives.

    Prints that are NOT inside any loop → emitted immediately, zero latency.
    No ``time.sleep()`` required anywhere in user code.
"""

from __future__ import annotations

import builtins
import dis
import opcode
import queue
import sys
import threading
from typing import Any, TextIO

from chadconsole.data_analyzer import ErrorPayload, InputRequest, Payload, analyze


# ---------------------------------------------------------------------------
# Bytecode constants (resolved once at import time for this Python version)
# ---------------------------------------------------------------------------

_FOR_ITER     = opcode.opmap.get("FOR_ITER")
_JUMP_BACKWARD = opcode.opmap.get("JUMP_BACKWARD")


# ---------------------------------------------------------------------------
# Loop detection helpers
# ---------------------------------------------------------------------------

def _is_frame_in_for_loop(frame) -> tuple | None:
    """Check if *frame* is currently executing inside a ``for`` loop body.

    Returns a hashable key ``(filename, code_obj_id, for_iter_offset)``
    uniquely identifying this loop, or ``None`` if the frame is not in a loop.
    """
    if _FOR_ITER is None or _JUMP_BACKWARD is None:
        return None  # Unsupported Python version — degrade gracefully

    code = frame.f_code
    current_offset = frame.f_lasti

    try:
        instructions = list(dis.get_instructions(code))
    except Exception:
        return None

    # Map: FOR_ITER.offset  -> END_FOR offset (via FOR_ITER.argval)
    # Map: FOR_ITER.offset  -> JUMP_BACKWARD.offset (who jumps back here)
    for_iters: dict[int, int] = {}   # for_iter_offset -> end_for_offset
    jump_backs: dict[int, int] = {}  # for_iter_offset -> jump_backward_offset

    for instr in instructions:
        if instr.opcode == _FOR_ITER:
            for_iters[instr.offset] = instr.argval   # argval = END_FOR target
        elif instr.opcode == _JUMP_BACKWARD:
            # argval is the target offset (the FOR_ITER we jump back to)
            jump_backs[instr.argval] = instr.offset

    for for_iter_off, end_for_off in for_iters.items():
        jump_back_off = jump_backs.get(for_iter_off)
        if jump_back_off is None:
            continue
        # Loop body occupies instructions from (for_iter_off + 2) to jump_back_off
        body_start = for_iter_off + 2
        body_end   = jump_back_off
        if body_start <= current_offset <= body_end:
            return (code.co_filename, id(code), for_iter_off)

    return None


def _caller_loop_key(skip: int = 2) -> tuple | None:
    """Walk the call stack starting *skip* frames up and find the first
    frame that is executing inside a ``for`` loop.

    Returns the loop key, or ``None`` if no enclosing loop is found.
    We search up to 8 frames deep to handle prints inside helper functions
    that are called from within a loop.
    """
    try:
        frame = sys._getframe(skip)
    except ValueError:
        return None

    for _ in range(8):
        if frame is None:
            break
        key = _is_frame_in_for_loop(frame)
        if key is not None:
            return key
        frame = frame.f_back

    return None


# ---------------------------------------------------------------------------
# ConsoleWriter — replacement for sys.stdout
# ---------------------------------------------------------------------------

class ConsoleWriter:
    """A file-like object that captures direct sys.stdout.write() calls.

    Any code doing ``sys.stdout.write(...)`` directly (e.g. logging, third-party
    libs) is captured here and emitted as a standard payload immediately.
    """

    def __init__(self, output_queue: queue.Queue, original: TextIO) -> None:
        self._queue = output_queue
        self._original = original
        self.encoding = getattr(original, "encoding", "utf-8")

    def write(self, text: str) -> int:
        """Capture direct stdout writes as standard payloads."""
        if text and text.strip():
            payload = Payload(tag="standard", content=text.rstrip("\n"))
            self._queue.put(payload)
        return len(text)

    def flush(self) -> None:
        """No-op — the GUI doesn't need flushing."""

    def fileno(self) -> int:
        """Delegate to original stdout for compatibility."""
        return self._original.fileno()

    def isatty(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# LoopGrouper — structural, deterministic loop grouping
# ---------------------------------------------------------------------------

class _LoopGrouper:
    """Groups consecutive print() calls that originate from the SAME ``for`` loop.

    Algorithm:
    1. On each print(), inspect the call stack to get a ``loop_key``.
    2. ``loop_key is None``  → not in a loop → flush any pending buffer, emit immediately.
    3. ``loop_key == self._current_key`` → same loop, same iteration → append to buffer.
    4. ``loop_key != self._current_key`` → new/different loop → flush old buffer, start new.

    When the buffer is flushed, it becomes a single ``loop_pattern`` Payload.

    Thread-safe via a Lock (multiple threads can call print() concurrently).
    """

    def __init__(self, output_queue: queue.Queue) -> None:
        self._queue = output_queue
        self._lock = threading.Lock()
        self._buffer: list[str] = []
        self._current_key: tuple | None = None

    def submit(self, payload: Payload) -> None:
        """Route a payload — either buffer it (loop) or emit immediately (non-loop)."""
        # skip=3: submit() → custom_print() → caller's frame
        loop_key = _caller_loop_key(skip=3)

        with self._lock:
            if loop_key is None:
                # ── Not in a for-loop ─────────────────────────────────
                self._flush_locked()
                self._queue.put(payload)

            elif loop_key == self._current_key:
                # ── Same loop — accumulate ────────────────────────────
                self._buffer.append(payload.content)

            else:
                # ── New loop (or first loop print) ────────────────────
                self._flush_locked()
                self._current_key = loop_key
                self._buffer.append(payload.content)

    def flush(self) -> None:
        """Public flush — call this before input() or at script end."""
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        """Emit buffer as a single loop_pattern payload. Must hold ``_lock``."""
        if not self._buffer:
            self._current_key = None
            return
        content = "\n".join(self._buffer)
        self._buffer.clear()
        self._current_key = None
        self._queue.put(Payload(tag="loop_pattern", content=content))


# ---------------------------------------------------------------------------
# Input handler
# ---------------------------------------------------------------------------

class _InputHandler:
    """Manages the input() interception lifecycle.

    When input() is called:
    1. Flush any pending loop buffer (so loop output appears before the prompt).
    2. Push an InputRequest to the queue (tells UI to show entry field).
    3. Block the calling thread on a threading.Event.
    4. The UI calls .resolve(value) when the user hits Enter.
    5. The Event is released and the value is returned to the caller.
    """

    def __init__(self, output_queue: queue.Queue, grouper: _LoopGrouper) -> None:
        self._queue = output_queue
        self._grouper = grouper
        self._event = threading.Event()
        self._response: str = ""
        self._lock = threading.Lock()

    def request(self, prompt: str = "") -> str:
        """Called from the user's script thread — blocks until UI responds."""
        # Flush loop buffer so loop output isn't stuck behind the prompt
        self._grouper.flush()

        with self._lock:
            self._event.clear()
            self._response = ""

        # Signal the UI
        req = InputRequest(prompt=prompt, handler=self)
        self._queue.put(req)

        # Block until the UI resolves
        self._event.wait()
        return self._response

    def resolve(self, value: str) -> None:
        """Called from the UI thread when the user submits input."""
        self._response = value
        self._event.set()


# ---------------------------------------------------------------------------
# Installer — wires everything up
# ---------------------------------------------------------------------------

_original_print     = builtins.print
_original_input     = builtins.input
_original_stdout    = sys.stdout
_original_excepthook = sys.excepthook


def install(output_queue: queue.Queue) -> _InputHandler:
    """Install all interceptors. Returns the InputHandler for UI wiring.

    Call this once during chadconsole initialization.
    """
    # 1. Replace sys.stdout
    writer = ConsoleWriter(output_queue, _original_stdout)
    sys.stdout = writer  # type: ignore[assignment]

    # 2. Build the loop grouper (structural, zero-latency, no timers)
    grouper = _LoopGrouper(output_queue)

    # Flush any buffered loop output when the user's script finishes.
    # Without this, a for-loop at the END of a script (or as the ONLY thing)
    # would never flush — the output would be silently lost.
    #
    # Why not atexit?  atexit handlers only fire after ALL non-daemon threads
    # finish, but the UI thread is non-daemon (so it blocks atexit).  And when
    # the window closes, os._exit(0) skips atexit entirely.
    #
    # Solution: a tiny daemon thread that waits for the main thread to end,
    # then flushes the grouper.  The data lands in the queue and the UI thread
    # (still alive) picks it up and renders it.
    def _flush_on_main_exit() -> None:
        threading.main_thread().join()
        grouper.flush()

    threading.Thread(
        target=_flush_on_main_exit, daemon=True, name="ChadConsole-Flush"
    ).start()

    # 3. Replace builtins.print
    def custom_print(*args: Any, sep: str = " ", end: str = "\n", **kwargs: Any) -> None:
        """Loop-aware, zero-latency print() replacement."""
        payload = analyze(*args, sep=sep)
        grouper.submit(payload)

    builtins.print = custom_print  # type: ignore[assignment]

    # 4. Replace builtins.input
    handler = _InputHandler(output_queue, grouper)

    def custom_input(prompt: str = "") -> str:
        """Blocking input() replacement — signals UI for entry field."""
        return handler.request(prompt)

    builtins.input = custom_input  # type: ignore[assignment]

    # 5. Install sys.excepthook to catch ALL unhandled exceptions
    #    and display them as red ErrorBlocks in the GUI.
    import traceback as _tb

    def custom_excepthook(exc_type, exc_value, exc_tb) -> None:
        """Intercept unhandled exceptions — flush loop buffer then send ErrorPayload."""
        # Flush any buffered loop lines so they appear before the error
        grouper.flush()
        # Format the full traceback text
        full_tb = "".join(_tb.format_exception(exc_type, exc_value, exc_tb)).rstrip()
        err = ErrorPayload(
            error_type=exc_type.__name__,
            message=str(exc_value),
            traceback=full_tb,
        )
        output_queue.put(err)

    sys.excepthook = custom_excepthook

    return handler


def uninstall() -> None:
    """Restore original print, input, stdout, and excepthook."""
    builtins.print = _original_print
    builtins.input = _original_input
    sys.stdout     = _original_stdout
    sys.excepthook = _original_excepthook
