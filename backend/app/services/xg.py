from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.core.config import settings

try:
    import joblib
except Exception:  # pragma: no cover - optional at import time in minimal environments
    joblib = None


def shot_geometry(x: float, y: float) -> tuple[float, float]:
    """StatsBomb coordinates: 120 x 80, attacking goal centred at (120, 40)."""
    dx = max(0.001, 120.0 - float(x))
    dy = abs(40.0 - float(y))
    distance = math.sqrt(dx * dx + dy * dy)
    left = math.atan2(44.0 - float(y), dx)
    right = math.atan2(36.0 - float(y), dx)
    angle = abs(left - right)
    return distance, angle


class XGService:
    def __init__(self) -> None:
        self.model_path = Path(settings.xg_model_path)
        self.card_path = Path(settings.xg_model_card_path)
        self.model = None
        self.card: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if joblib and self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
            except Exception:
                self.model = None
        if self.card_path.exists():
            try:
                self.card = json.loads(self.card_path.read_text())
            except Exception:
                self.card = {}

    def status(self) -> dict:
        return {
            'trained_model_loaded': self.model is not None,
            'model_path': str(self.model_path),
            'model_card': self.card or None,
            'fallback': 'transparent geometric logistic baseline',
            'training_source': 'StatsBomb Open Data when train_xg.py is run',
        }

    def predict(self, shot: dict) -> dict:
        distance, angle = shot_geometry(float(shot['x']), float(shot['y']))
        features = {
            'distance': distance,
            'angle': angle,
            'under_pressure': bool(shot.get('under_pressure', False)),
            'first_time': bool(shot.get('first_time', False)),
            'body_part': shot.get('body_part') or 'Unknown',
            'play_pattern': shot.get('play_pattern') or 'Unknown',
        }
        if self.model is not None:
            import pandas as pd
            frame = pd.DataFrame([features])
            p = float(self.model.predict_proba(frame)[0][1])
            mode = 'trained-statsbomb-model'
        else:
            logit = 2.5 - 0.115 * distance + 1.65 * angle - (0.32 if features['under_pressure'] else 0)
            p = 1 / (1 + math.exp(-logit))
            mode = 'geometric-baseline'
        return {'xg': round(max(0.001, min(0.999, p)), 4), 'model': mode, 'features': features}


xg_service = XGService()
