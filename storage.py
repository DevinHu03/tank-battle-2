"""Versioned, atomic campaign persistence."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from game import CampaignState

SAVE_VERSION = 2


class CampaignStore:
    def __init__(self, path: str | Path | None = None) -> None:
        default_dir = Path(os.environ.get("APPDATA", Path.home())) / "SteelFrontline"
        self.path = Path(path) if path is not None else default_dir / "save.json"
        self.data = self._load()

    @staticmethod
    def defaults() -> dict:
        return {"version": SAVE_VERSION, "campaign": None, "levels": {}, "best_campaign_score": 0, "cleared": False,
                "settings": {"music": True, "sound": True, "fullscreen": False}}

    def _load(self) -> dict:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict): raise ValueError
            if "version" not in raw:  # v1 high-score migration
                return {**self.defaults(), "best_campaign_score": max(0, int(raw.get("high_score", 0))), "cleared": bool(raw.get("cleared", False))}
            data = self.defaults(); data.update(raw); data["settings"] = {**self.defaults()["settings"], **raw.get("settings", {})}
            if data["campaign"] is not None and not isinstance(data["campaign"], dict): data["campaign"] = None
            return data
        except (OSError, ValueError, TypeError, json.JSONDecodeError): return self.defaults()

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2); temporary = handle.name
            os.replace(temporary, self.path); return True
        except OSError: return False

    def campaign(self) -> CampaignState | None:
        raw = self.data["campaign"]
        if not raw: return None
        try: return CampaignState(max(1, int(raw["current_level"])), {str(k): int(v) for k, v in raw.get("upgrades", {}).items()}, int(raw.get("score", 0)), float(raw.get("elapsed", 0)))
        except (KeyError, TypeError, ValueError): return None

    def save_campaign(self, state: CampaignState | None) -> bool:
        self.data["campaign"] = None if state is None else {"current_level": state.current_level, "upgrades": state.upgrades, "score": state.score, "elapsed": state.elapsed}
        return self.save()

    def record_level(self, level: int, score: int, elapsed: float, grade: str) -> bool:
        previous = self.data["levels"].get(str(level), {}); self.data["levels"][str(level)] = {
            "best_score": max(int(previous.get("best_score", 0)), score), "best_time": min(float(previous.get("best_time", elapsed)), elapsed),
            "best_grade": min(str(previous.get("best_grade", "C")), grade, key="SABC".index)}
        self.data["best_campaign_score"] = max(self.data["best_campaign_score"], score); return self.save()


class ScoreStore:
    """Compatibility façade for the former two-field save API."""
    def __init__(self, path: str | Path | None = None) -> None:
        self.store = CampaignStore(path); self.high_score = self.store.data["best_campaign_score"]; self.cleared = self.store.data["cleared"]

    def record(self, score: int, cleared: bool = False) -> bool:
        changed = score > self.high_score or (cleared and not self.cleared)
        if not changed: return False
        self.high_score = max(score, self.high_score); self.cleared = self.cleared or cleared
        self.store.data["best_campaign_score"] = self.high_score; self.store.data["cleared"] = self.cleared
        return self.store.save()
