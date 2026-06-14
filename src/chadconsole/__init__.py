"""
chadconsole
~~~~~~~~~~~

Just ``import chadconsole`` and all your print() and input() calls
are routed to a beautiful dark-mode GUI window.

Architecture:
    1. A shared queue.Queue connects the script thread to the UI thread.
    2. core_interceptor replaces sys.stdout, builtins.print, builtins.input.
    3. ui_engine.PrettyConsoleApp runs Tk mainloop in a NON-daemon thread
       so the window stays alive even after the user's script finishes.
    4. The user's script continues executing on the main thread.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__: list[str] = []

import atexit
import os
import queue
import sys
import threading

from chadconsole.core_interceptor import install, uninstall
from chadconsole.ui_engine import PrettyConsoleApp


# ---------------------------------------------------------------------------
# Shared communication channel
# ---------------------------------------------------------------------------

_output_queue: queue.Queue = queue.Queue()

# ---------------------------------------------------------------------------
# Install interceptors
# ---------------------------------------------------------------------------

_input_handler = install(_output_queue)

# ---------------------------------------------------------------------------
# Launch the UI in a NON-daemon thread (keeps process alive until window closes)
# ---------------------------------------------------------------------------

_app: PrettyConsoleApp | None = None
_ui_ready = threading.Event()


def _run_ui() -> None:
    """Entry point for the UI thread.

    This is a NON-daemon thread so the window stays open even after the
    user's main script finishes executing. The process exits only when
    the user closes the GUI window.
    """
    global _app
    try:
        _app = PrettyConsoleApp(_output_queue)
        _app.set_input_handler(_input_handler)
        _ui_ready.set()
        _app.mainloop()
    except Exception:
        import traceback
        sys.__stderr__.write(f"[ChadConsole] UI thread crashed:\n{traceback.format_exc()}\n")
        _ui_ready.set()  # Unblock main thread even on failure
    finally:
        # When the window is closed (mainloop exits), clean up and exit
        uninstall()
        os._exit(0)  # Clean exit — suppresses Tcl_AsyncDelete noise


# NON-daemon thread: process stays alive until this thread ends (window closed)
_ui_thread = threading.Thread(target=_run_ui, daemon=False, name="ChadConsole-UI")
_ui_thread.start()

# Wait for the UI to be ready before the script proceeds
_ui_ready.wait(timeout=5.0)
