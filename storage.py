"""Small, failure-tolerant high-score persistence."""

from __future__ import annotations

import json
from pathlib import Path


class ScoreStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else Path(__file__).with_name("save.json")
        self.high_score, self.cleared = self._load()

    def _load(self) -> tuple[int, bool]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return int(data.get("high_score", 0)), bool(data.get("cleared", False))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0, False

    def record(self, score: int, cleared: bool = False) -> bool:
        changed = score > self.high_score or cleared and not self.cleared
        if not changed:
            return False
        self.high_score = max(score, self.high_score)
        self.cleared = self.cleared or cleared
        try:
            self.path.write_text(json.dumps({"high_score": self.high_score, "cleared": self.cleared}, ensure_ascii=False), encoding="utf-8")
            return True
        except OSError:
            return False
