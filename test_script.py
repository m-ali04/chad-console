"""
test_script.py — PrettyConsole Demo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Demonstrates all chadconsole features:
  1. Standard text prints
  2. Deeply nested dictionary
  3. List and tuple prints
  4. For loop (star pyramid pattern)
  5. For loop (numbered sequence)
  6. User input() request

No time.sleep() needed — loop detection is structural, not timing-based.
"""

import sys
sys.path.insert(0, "src")

import chadconsole  # noqa: E402 — activates the GUI hijack


# ── 1. Standard text prints ──────────────────────────────────────────────

print("Hello from PrettyConsole! 🚀")

print("This is a standard text output routed to the GUI.")

print("Each print becomes a separate visual block with a blue accent bar.")


# ── 2. Deeply nested dictionary ──────────────────────────────────────────

user_data = {
    "user": {
        "name": "Ali",
        "role": "Engineer",
        "preferences": {
            "theme": "dark",
            "language": "Python",
            "editor": {
                "name": "VS Code",
                "extensions": ["Pylance", "GitLens", "Thunder Client"],
                "settings": {
                    "font_size": 14,
                    "tab_size": 4,
                    "auto_save": True,
                },
            },
        },
        "projects": ["chadconsole", "chad-console", "api-gateway"],
    },
    "metadata": {
        "version": "0.1.0",
        "timestamp": "2026-06-13T23:00:00Z",
    },
}

print(user_data)


# ── 3. List print ────────────────────────────────────────────────────────

fibonacci = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]
print(fibonacci)


# ── 4. Tuple print ───────────────────────────────────────────────────────

coordinates = (
    ("New York", 40.7128, -74.0060),
    ("London", 51.5074, -0.1278),
    ("Tokyo", 35.6762, 139.6503),
    ("Sydney", -33.8688, 151.2093),
)
print(coordinates)


# ── 5. For loop — star pyramid (grouped as loop_pattern) ─────────────────

for i in range(1, 16):
    print(" " * (15 - i) + "*" * (2 * i - 1))


# ── 6. Another for loop — numbered sequence ──────────────────────────────

for i in range(1, 11):
    print(f"  [{i:02d}] Processing item {i}... ✓")


# ── 7. User input ────────────────────────────────────────────────────────

name = input("What is your name? → ")
print(f"Welcome aboard, {name}! 🎉")

favorite = input("What's your favorite language? → ")
print(f"Great choice! {favorite} is awesome. 🔥")

print("Demo complete. Close the window or press Ctrl+C to exit.")

# Keep the script alive so the GUI stays open
try:
    while True:
        import time
        time.sleep(50)
except KeyboardInterrupt:
    pass
