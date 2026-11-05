from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.entities import Favorite, User
from app.providers.football_data import provider
from app.services.analyst import analyst_for_match
from app.services.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.services.cache import cache
from app.services.demo import DemoMatchEngine
from app.services.demo_sessions import sessions
from app.services.prediction import analyst_summary, live_win_probability
from app.services.provider_quota import ProviderQuotaExceeded
from app.services.websocket_manager import ws_manager
from app.services.xg import xg_service

router = APIRouter()


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class FavoriteBody(BaseModel):
    entity_type: str = Field(pattern='^(team|competition)$')
    entity_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)


class ShotBody(BaseModel):
    x: float = Field(ge=0, le=120)
    y: float = Field(ge=0, le=80)
    under_pressure: bool = False
    first_time: bool = False
    body_part: str = Field(default='Unknown', max_length=80)
    play_pattern: str = Field(default='Unknown', max_length=80)


def provider_unconfigured_payload() -> dict:
    return {
        'configured': False,
        'provider': 'football-data.org',
        'message': 'Add FOOTBALL_DATA_API_KEY to .env to enable real data. Demo Lab works without a key.',
        'matches': [],
    }


def validated_competition(code: str) -> str:
    normalized = code.upper()
    if normalized not in settings.competition_codes:
        raise HTTPException(status_code=400, detail='Unsupported competition code.')
    return normalized


async def current_user(request: Request, authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get('sip_access')
    if authorization and authorization.lower().startswith('bearer '):
        token = authorization.split(' ', 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail='Authentication required.')
    try:
        payload = decode_access_token(token)
        user_id = int(payload['sub'])
    except Exception as exc:
        raise HTTPException(status_code=401, detail='Invalid or expired token.') from exc
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail='User not available.')
    return user


async def remembered(key: str, ttl: int, stale_ttl: int, loader):
    try:
        return await cache.remember_json(key, ttl, stale_ttl, loader)
    except ProviderQuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={'Retry-After': '60'}) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Real-data provider unavailable: {exc}') from exc


@router.get('/config')
async def config():
    return {
        'app_name': settings.app_name,
        'environment': settings.app_env,
        'real_data_configured': provider.configured,
        'provider': 'football-data.org',
        'competitions': settings.competition_codes,
        'demo_available': True,
        'attribution': 'Data provided by football-data.org',
        'crest_policy': settings.crest_policy,
        'provider_rpm_budget': settings.provider_rpm_budget,
        'llm_analyst_enabled': bool(settings.enable_llm_analyst and settings.openai_api_key),
        'xg': xg_service.status(),
    }


@router.get('/ml/status')
async def ml_status():
    return {'xg': xg_service.status(), 'win_probability': {'model': 'explainable-baseline-v1', 'trained': False}}


@router.post('/ml/xg/predict')
async def xg_predict(body: ShotBody):
    return xg_service.predict(body.model_dump())


@router.get('/competitions')
async def competitions():
    labels = {'PL':'Premier League','CL':'UEFA Champions League','PD':'La Liga','BL1':'Bundesliga','SA':'Serie A','FL1':'Ligue 1'}
    return [{'code': c, 'name': labels.get(c, c)} for c in settings.competition_codes]


@router.get('/matches/live')
async def live_matches():
    if not provider.configured:
        return provider_unconfigured_payload()
    matches, source = await remembered('api:live_matches', max(10, settings.live_poll_seconds - 2), 300, provider.live_matches)
    return {'configured': True, 'provider': 'football-data.org', 'source': source, 'matches': matches}


@router.get('/matches/upcoming')
async def upcoming_matches():
    if not provider.configured:
        return provider_unconfigured_payload()
    key = f'api:upcoming:{settings.upcoming_days}'
    matches, source = await remembered(key, 300, 3600, provider.upcoming_matches)
    return {'configured': True, 'provider': 'football-data.org', 'source': source, 'matches': matches}


@router.get('/matches/recent/{competition}')
async def recent_matches(competition: str):
    if not provider.configured:
        return provider_unconfigured_payload()
    code = validated_competition(competition)
    matches, source = await remembered(f'recent:{code}', 600, 7200, lambda: provider.recent_matches(code))
    return {'configured': True, 'provider': 'football-data.org', 'source': source, 'matches': matches}


@router.get('/matches/{match_id}')
async def match_detail(match_id: int):
    if not provider.configured:
        raise HTTPException(status_code=409, detail='Real-data mode is not configured.')
    data, _ = await remembered(f'match:detail:{match_id}', 60, 1800, lambda: provider.match_detail(match_id))
    return data


@router.get('/competitions/{competition}/standings')
async def standings(competition: str):
    if not provider.configured:
        raise HTTPException(status_code=409, detail='Real-data mode is not configured.')
    code = validated_competition(competition)
    data, _ = await remembered(f'standings:{code}', 900, 21600, lambda: provider.standings(code))
    return data


@router.get('/competitions/{competition}/scorers')
async def scorers(competition: str):
    if not provider.configured:
        raise HTTPException(status_code=409, detail='Real-data mode is not configured.')
    code = validated_competition(competition)
    data, _ = await remembered(f'scorers:{code}', 900, 21600, lambda: provider.scorers(code))
    return data


@router.get('/competitions/{competition}/teams')
async def competition_teams(competition: str):
    if not provider.configured:
        raise HTTPException(status_code=409, detail='Real-data mode is not configured.')
    code = validated_competition(competition)
    teams, _ = await remembered(f'teams:{code}', 1800, 86400, lambda: provider.competition_teams(code))
    return {'teams': teams}


@router.get('/teams/{team_id}')
async def team_detail(team_id: int):
    if not provider.configured:
        raise HTTPException(status_code=409, detail='Real-data mode is not configured.')
    data, _ = await remembered(f'team:{team_id}', 1800, 86400, lambda: provider.team_detail(team_id))
    return data


@router.post('/matches/{match_id}/predict')
async def predict_match(match_id: int):
    if not provider.configured:
        raise HTTPException(status_code=409, detail='Real-data mode is not configured.')
    match, _ = await remembered(f'match:detail:{match_id}', 60, 1800, lambda: provider.match_detail(match_id))
    probabilities = live_win_probability(match)
    return {
        'match': match,
        'probabilities': probabilities,
        'analysis': await analyst_for_match(match, probabilities),
        'model_card': {
            'type': 'transparent heuristic baseline',
            'features': ['score difference', 'match minute', 'home advantage'],
            'claim': 'Not presented as a trained ML model.',
        },
    }


@router.post('/demo/sessions')
async def create_demo_session():
    session_id, snapshot = await sessions.create()
    snapshot['probabilities'] = live_win_probability(snapshot['match'])
    snapshot['analysis'] = analyst_summary(snapshot['match'], snapshot['probabilities'])
    return {'session_id': session_id, 'snapshot': snapshot}


@router.get('/demo/snapshot')
async def demo_snapshot():
    engine = DemoMatchEngine()
    snapshot = engine.tick()
    snapshot['probabilities'] = live_win_probability(snapshot['match'])
    snapshot['analysis'] = analyst_summary(snapshot['match'], snapshot['probabilities'])
    return snapshot


@router.websocket('/ws/demo/{session_id}')
async def demo_ws_session(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            snapshot = await sessions.tick(session_id)
            snapshot['probabilities'] = live_win_probability(snapshot['match'])
            snapshot['analysis'] = analyst_summary(snapshot['match'], snapshot['probabilities'])
            await websocket.send_json(snapshot)
            await asyncio.sleep(2.5)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/demo')
async def demo_ws_legacy(websocket: WebSocket):
    """Backward-compatible isolated demo stream; each socket gets its own engine."""
    engine = DemoMatchEngine()
    await websocket.accept()
    try:
        while True:
            snapshot = engine.tick()
            snapshot['probabilities'] = live_win_probability(snapshot['match'])
            snapshot['analysis'] = analyst_summary(snapshot['match'], snapshot['probabilities'])
            await websocket.send_json(snapshot)
            await asyncio.sleep(2.5)
    except WebSocketDisconnect:
        return


@router.websocket('/ws/live')
async def live_ws(websocket: WebSocket):
    await ws_manager.connect(websocket)
    await websocket.send_json({
        'type': 'connection',
        'real_data_configured': provider.configured,
        'message': 'Subscribed to real-data event stream.' if provider.configured else 'Provider key not configured.',
    })
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key='sip_access', value=token, httponly=True, secure=settings.is_production,
        samesite='strict' if settings.is_production else 'lax',
        max_age=settings.access_token_minutes * 60, path='/',
    )


@router.post('/auth/register')
async def register(body: RegisterBody, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail='Email already registered.')
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(str(user.id))
    _set_auth_cookie(response, token)
    return {'id': user.id, 'email': user.email, 'authenticated': True}


@router.post('/auth/login')
async def login(body: LoginBody, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password.')
    token = create_access_token(str(user.id))
    _set_auth_cookie(response, token)
    return {'id': user.id, 'email': user.email, 'authenticated': True}


@router.get('/auth/me')
async def me(user: User = Depends(current_user)):
    return {'id': user.id, 'email': user.email}


@router.post('/auth/logout')
async def logout(response: Response):
    response.delete_cookie('sip_access', path='/')
    return {'logged_out': True}


@router.get('/favorites')
async def list_favorites(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Favorite).where(Favorite.user_id == user.id))).all()
    return [
        {
            'id': row.id,
            'entity_type': row.entity_type,
            'entity_id': row.entity_id,
            'label': row.label,
        }
        for row in rows
    ]


@router.post('/favorites')
async def add_favorite(body: FavoriteBody, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(Favorite).where(
        Favorite.user_id == user.id,
        Favorite.entity_type == body.entity_type,
        Favorite.entity_id == body.entity_id,
    ))
    if existing:
        return {
            'id': existing.id,
            'entity_type': existing.entity_type,
            'entity_id': existing.entity_id,
            'label': existing.label,
        }
    row = Favorite(user_id=user.id, entity_type=body.entity_type, entity_id=body.entity_id, label=body.label)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        'id': row.id,
        'entity_type': row.entity_type,
        'entity_id': row.entity_id,
        'label': row.label,
    }


@router.delete('/favorites/{favorite_id}')
async def delete_favorite(favorite_id: int, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(Favorite, favorite_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail='Favorite not found.')
    await db.delete(row)
    await db.commit()
    return {'deleted': True}
