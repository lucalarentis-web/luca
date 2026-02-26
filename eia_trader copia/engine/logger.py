from __future__ import annotations
from pathlib import Path
from datetime import datetime


class Logger:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, level: str, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts}\t{level}\t{msg}\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)

    def info(self, msg: str): self._write("INFO", msg)
    def warn(self, msg: str): self._write("WARN", msg)
    def error(self, msg: str): self._write("ERROR", msg)
