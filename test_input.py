"""Minimal input test — logs all errors to a file."""
import sys, os, traceback
sys.path.insert(0, "src")

# Set up error logging to file
err_log = open("error_log.txt", "w")

def log_error(msg):
    err_log.write(msg + "\n")
    err_log.flush()

# Patch stderr to capture everything
class ErrCapture:
    def write(self, s):
        err_log.write(s)
        err_log.flush()
    def flush(self):
        err_log.flush()

sys.stderr = ErrCapture()
sys.__stderr__ = ErrCapture()

log_error("=== Starting import ===")

try:
    import chadconsole
    log_error("=== Import OK ===")
except Exception as e:
    log_error(f"Import error: {traceback.format_exc()}")

import time
time.sleep(1)

log_error("=== Printing standard text ===")
print("Hello!")
time.sleep(0.5)

log_error("=== Calling input() ===")
try:
    name = input("Your name? ")
    log_error(f"=== Input returned: {name} ===")
    print(f"Got: {name}")
except Exception as e:
    log_error(f"Input error: {traceback.format_exc()}")

time.sleep(2)
log_error("=== Keeping alive ===")

try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    pass
