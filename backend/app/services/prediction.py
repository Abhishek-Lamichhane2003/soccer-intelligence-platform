from __future__ import annotations
from math import exp


def _softmax(values: list[float]) -> list[float]:
    exps = [exp(v) for v in values]
    total = sum(exps)
    return [v / total for v in exps]


def live_win_probability(match: dict) -> dict:
    """Explainable baseline, not a betting model.

    Uses score differential, match minute and a small home advantage. It is intentionally
    transparent so the UI can explain every probability. A trained model can replace this
    service later without changing the API contract.
    """
    score = match.get('score') or {}
    home = score.get('home')
    away = score.get('away')
    if home is None or away is None:
        home = away = 0

    minute = match.get('minute')
    if minute is None:
        minute = 0 if match.get('status') in {'SCHEDULED', 'TIMED'} else 45
    minute = max(0, min(int(minute), 120))

    remaining_factor = max(0.08, (90 - min(minute, 90)) / 90)
    diff = home - away

    home_logit = 0.22 + (1.35 * diff) / max(0.35, remaining_factor)
    away_logit = -0.10 - (1.35 * diff) / max(0.35, remaining_factor)
    draw_logit = 0.30 - abs(diff) * (1.9 - remaining_factor)

    h, d, a = _softmax([home_logit, draw_logit, away_logit])
    return {
        'home': round(h * 100, 1),
        'draw': round(d * 100, 1),
        'away': round(a * 100, 1),
        'model': 'explainable-baseline-v1',
        'disclaimer': 'Portfolio analytics baseline; not intended for betting or wagering.',
        'features': {
            'score_difference': diff,
            'minute': minute,
            'home_advantage': 0.22,
        },
    }


def analyst_summary(match: dict, probabilities: dict) -> dict:
    home = match['home_team']['short_name'] or match['home_team']['name']
    away = match['away_team']['short_name'] or match['away_team']['name']
    sh = match['score']['home']
    sa = match['score']['away']
    minute = match.get('minute') or 0

    if sh is None or sa is None:
        headline = f'{home} vs {away} is scheduled.'
        detail = 'The model starts near a balanced prior with a small home-field adjustment.'
    elif sh == sa:
        headline = f'{home} and {away} are level at {sh}-{sa}.'
        detail = f'At minute {minute}, the draw remains meaningful because the score is tied and time is decreasing.'
    elif sh > sa:
        headline = f'{home} lead {sh}-{sa}.'
        detail = f'The home win probability rises as the lead is protected deeper into the match; the remaining-time factor is now lower.'
    else:
        headline = f'{away} lead {sa}-{sh}.'
        detail = f'The away win probability rises because the visitors hold the score advantage with fewer minutes remaining.'

    return {
        'headline': headline,
        'detail': detail,
        'confidence': max(probabilities['home'], probabilities['draw'], probabilities['away']),
        'generated_by': 'local-explainable-analyst',
    }
