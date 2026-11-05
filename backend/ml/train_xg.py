"""Train an xG classifier from StatsBomb Open Data.

Usage from backend/: python -m ml.train_xg --competition-id 43 --season-id 106 --max-matches 40
The script downloads public match/event JSON, extracts shots, trains a time-independent
shot-level classifier, reports ROC-AUC/log-loss/Brier score, and writes a model + model card.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from urllib.request import urlopen

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE = 'https://raw.githubusercontent.com/statsbomb/open-data/master/data'
ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'models'


def fetch_json(url: str):
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def geometry(x: float, y: float):
    dx = max(0.001, 120.0 - x)
    dy = abs(40.0 - y)
    distance = math.sqrt(dx * dx + dy * dy)
    angle = abs(math.atan2(44.0 - y, dx) - math.atan2(36.0 - y, dx))
    return distance, angle


def extract_shots(events: list[dict]) -> list[dict]:
    rows = []
    for event in events:
        if (event.get('type') or {}).get('name') != 'Shot' or not event.get('location'):
            continue
        x, y = event['location'][:2]
        shot = event.get('shot') or {}
        distance, angle = geometry(float(x), float(y))
        rows.append({
            'distance': distance,
            'angle': angle,
            'under_pressure': bool(event.get('under_pressure', False)),
            'first_time': bool(shot.get('first_time', False)),
            'body_part': (shot.get('body_part') or {}).get('name', 'Unknown'),
            'play_pattern': (event.get('play_pattern') or {}).get('name', 'Unknown'),
            'match_id': event.get('match_id'),
            'goal': int((shot.get('outcome') or {}).get('name') == 'Goal'),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--competition-id', type=int, default=43, help='StatsBomb competition ID')
    parser.add_argument('--season-id', type=int, default=106, help='StatsBomb season ID')
    parser.add_argument('--max-matches', type=int, default=50)
    args = parser.parse_args()

    matches = fetch_json(f'{BASE}/matches/{args.competition_id}/{args.season_id}.json')[:args.max_matches]
    rows = []
    for i, match in enumerate(matches, 1):
        match_id = match['match_id']
        print(f'[{i}/{len(matches)}] events {match_id}')
        events = fetch_json(f'{BASE}/events/{match_id}.json')
        for event in events:
            event['match_id'] = match_id
        rows.extend(extract_shots(events))
    if len(rows) < 200:
        raise SystemExit(f'Not enough shot samples ({len(rows)}). Increase --max-matches or choose another season.')

    df = pd.DataFrame(rows)
    y = df['goal']
    groups = df['match_id']
    X = df.drop(columns=['goal', 'match_id'])
    splitter = GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    numeric = ['distance', 'angle']
    categorical = ['body_part', 'play_pattern']
    binary = ['under_pressure', 'first_time']
    pre = ColumnTransformer([
        ('num', StandardScaler(), numeric),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical),
        ('bin', 'passthrough', binary),
    ])
    model = Pipeline([('preprocess', pre), ('classifier', LogisticRegression(max_iter=1500))])
    model.fit(X_train, y_train)
    prob = model.predict_proba(X_test)[:, 1]
    metrics = {
        'roc_auc': round(float(roc_auc_score(y_test, prob)), 4),
        'log_loss': round(float(log_loss(y_test, prob)), 4),
        'brier': round(float(brier_score_loss(y_test, prob)), 4),
    }
    MODELS.mkdir(exist_ok=True)
    joblib.dump(model, MODELS / 'xg_model.joblib')
    card = {
        'name': 'StatsBomb Open Data xG Logistic Regression',
        'source': 'StatsBomb Open Data',
        'competition_id': args.competition_id,
        'season_id': args.season_id,
        'matches': len(matches),
        'shots': len(df),
        'positive_rate': round(float(y.mean()), 4),
        'features': numeric + categorical + binary,
        'split': '75/25 GroupShuffleSplit by match_id, random_state=42 (prevents same-match leakage)',
        'metrics': metrics,
        'intended_use': 'portfolio/educational soccer analytics; not betting advice',
        'limitations': 'Shot-only model; does not include goalkeeper position, freeze-frame defenders, or temporal sequence context.',
        'attribution': 'StatsBomb Open Data',
    }
    (MODELS / 'xg_model_card.json').write_text(json.dumps(card, indent=2))
    print(json.dumps(card, indent=2))


if __name__ == '__main__':
    main()
