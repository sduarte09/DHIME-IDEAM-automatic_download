"""Progress file, so an interrupted run can continue where it stopped."""
from __future__ import annotations

import json
from pathlib import Path


class DownloadState:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.done: set[str] = set()
        self.missing: set[str] = set()
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.done, self.missing = set(data.get("done", [])), set(data.get("missing", []))

    @staticmethod
    def _key(code, chunk):
        return f"{code}|{chunk.key}"

    def is_done(self, code, chunk):
        return self._key(code, chunk) in self.done

    def mark_done(self, code, chunk):
        self.done.add(self._key(code, chunk))

    def mark_missing(self, code):
        self.missing.add(code)

    def save(self):
        if self.path:
            self.path.write_text(json.dumps({"done": sorted(self.done), "missing": sorted(self.missing)}, indent=1),
                                 encoding="utf-8")
