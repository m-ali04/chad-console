"""
error_test.py — Tests error display in ChadConsole
"""
import sys
sys.path.insert(0, "src")

import chadconsole

print("Starting error test...")
print("This line is fine ✓")

# This will cause a NameError — undefined variable
print(232 + 23)
