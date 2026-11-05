from __future__ import annotations

import json

import httpx

from app.core.config import settings
from app.services.prediction import analyst_summary


async def analyst_for_match(match: dict, probabilities: dict) -> dict:
    """Optional LLM analyst with a deterministic local fallback.

    The model receives only normalized match facts and is instructed not to invent
    unavailable player/event data. If no API key is configured, the local analyst
    is used and clearly labeled.
    """
    fallback = analyst_summary(match, probabilities)
    if not (settings.enable_llm_analyst and settings.openai_api_key):
        return fallback

    facts = {
        'competition': match.get('competition'),
        'home_team': match.get('home_team'),
        'away_team': match.get('away_team'),
        'score': match.get('score'),
        'minute': match.get('minute'),
        'status': match.get('status'),
        'goals': match.get('goals', []),
        'bookings': match.get('bookings', []),
        'substitutions': match.get('substitutions', []),
        'probabilities': probabilities,
    }
    prompt = (
        'You are a concise soccer match analyst. Use ONLY the supplied JSON facts. '
        'Do not invent players, statistics, tactics, injuries, or events. Explain in 2-3 sentences '
        'what currently drives the win/draw probabilities.\n\nFACTS:\n' + json.dumps(facts)
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                'https://api.openai.com/v1/responses',
                headers={'Authorization': f'Bearer {settings.openai_api_key}', 'Content-Type': 'application/json'},
                json={'model': settings.openai_model, 'input': prompt},
            )
            response.raise_for_status()
            body = response.json()
            text = body.get('output_text')
            if not text:
                chunks = []
                for item in body.get('output', []):
                    for content in item.get('content', []):
                        if content.get('type') in {'output_text', 'text'} and content.get('text'):
                            chunks.append(content['text'])
                text = '\n'.join(chunks).strip()
            if text:
                return {
                    'headline': 'AI match explanation',
                    'detail': text,
                    'confidence': fallback['confidence'],
                    'generated_by': f'openai-responses:{settings.openai_model}',
                    'grounding': 'normalized provider facts only',
                }
    except Exception:
        pass
    return fallback
