# ✦ ChadConsole

> Intercepts `print()` and `input()` — routes them to a beautiful dark-mode GUI.

## Installation

```bash
pip install chadconsole
```

## Usage

```python
import chadconsole  # That's it. All prints now go to the GUI.

print("Hello, world!")
print({"key": "value", "nested": [1, 2, 3]})

for i in range(5):
    print("*" * (i + 1))

name = input("What's your name? ")
print(f"Welcome, {name}!")
```

## Features

- **Zero config** — just `import chadconsole` at the top of your script
- **Auto type detection** — lists, dicts, tuples get special formatted rendering
- **Loop grouping** — `print()` calls inside `for` loops are automatically batched into a single visual block (bytecode-based detection, no `time.sleep()` needed)
- **Input interception** — `input()` calls display a floating entry field in the GUI
- **Dark neumorphic UI** — premium design with blue accents and monospace code rendering
- **Thread-safe** — your script runs normally; the GUI runs in a background thread

## License

MIT
