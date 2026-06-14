"""Integration test for chadconsole interceptors (no GUI)."""
import sys, queue
sys.path.insert(0, "src")

from chadconsole.core_interceptor import install, uninstall
from chadconsole.data_analyzer import Payload
import builtins

out = sys.__stdout__

# Install interceptors with a test queue
q = queue.Queue()
handler = install(q)

def drain():
    items = []
    while not q.empty():
        items.append(q.get_nowait())
    return items

# === Test 1: Simple prints (NOT in loop) ===
builtins.print("Hello World")
builtins.print("Standard output")

items = drain()
out.write(f"Test 1 — Got {len(items)} payloads (expected 2)\n")
for p in items:
    out.write(f"  tag={p.tag!r} content={p.content!r}\n")
assert len(items) == 2, f"Expected 2, got {len(items)}"
assert all(p.tag == "standard" for p in items)
out.write("  PASS\n\n")

# === Test 2: List/dict/tuple prints ===
builtins.print([1, 2, 3])
builtins.print({"a": 1, "b": 2})
builtins.print((10, 20))

items = drain()
out.write(f"Test 2 — Got {len(items)} payloads (expected 3)\n")
for p in items:
    out.write(f"  tag={p.tag!r}\n")
assert len(items) == 3
assert items[0].tag == "list"
assert items[1].tag == "dictionary"
assert items[2].tag == "tuple"
out.write("  PASS\n\n")

# === Test 3: For loop prints (should be grouped) ===
for i in range(5):
    builtins.print(f"Line {i}")

# Non-loop print triggers flush of loop buffer
builtins.print("After loop")

items = drain()
out.write(f"Test 3 — Got {len(items)} payloads (expected 2: loop_pattern + standard)\n")
for p in items:
    out.write(f"  tag={p.tag!r} content={repr(p.content[:60])}\n")
assert len(items) == 2, f"Expected 2, got {len(items)}: {[p.tag for p in items]}"
assert items[0].tag == "loop_pattern"
assert items[1].tag == "standard"
loop_lines = items[0].content.split("\n")
assert len(loop_lines) == 5, f"Expected 5 lines in loop, got {len(loop_lines)}"
out.write("  PASS\n\n")

# === Test 4: Two separate loops flush correctly ===
for i in range(3):
    builtins.print(f"Loop A line {i}")

for i in range(2):
    builtins.print(f"Loop B line {i}")

builtins.print("done")

items = drain()
out.write(f"Test 4 — Got {len(items)} payloads (expected 3: 2x loop_pattern + standard)\n")
for p in items:
    out.write(f"  tag={p.tag!r} content={repr(p.content[:60])}\n")
assert len(items) == 3, f"Got {len(items)}: {[p.tag for p in items]}"
assert items[0].tag == "loop_pattern"
assert items[1].tag == "loop_pattern"
assert items[2].tag == "standard"
out.write("  PASS\n\n")

# === Test 5: Mixed print (multiple args) ===
builtins.print("Total:", 42, "items")

items = drain()
out.write(f"Test 5 — Got {len(items)} payloads (expected 1)\n")
assert len(items) == 1
assert items[0].tag == "standard"
assert items[0].content == "Total: 42 items"
out.write(f"  content={items[0].content!r} PASS\n\n")

uninstall()
out.write("=" * 40 + "\n")
out.write("ALL TESTS PASSED!\n")
