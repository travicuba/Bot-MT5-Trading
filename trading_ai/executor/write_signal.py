import json
from pathlib import Path

def write_signal(signal: dict):
    path = Path("data/signal.json")
    path.parent.mkdir(exist_ok=True)

    with open(path, "w") as f:
        json.dump(signal, f, indent=2)