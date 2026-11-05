from __future__ import annotations

from datetime import date, timedelta
from typing import Any
import asyncio

import httpx

from app.core.config import settings
from app.services.provider_quota import ProviderQuotaExceeded, provider_quota


class ProviderConfigurationError(RuntimeError):
    pass


class FootballDataProvider:
    """Small adapter around football-data.org v4.

    The rest of the app consumes normalized objects so the UI is not coupled to
    provider-specific field names. Deep match fields are requested when available;
    plans without deep data simply return empty arrays and the UI explains that.
    """

    def __init__(self) -> None:
        self.base_url = settings.football_data_base_url.rstrip('/')
        self.token = settings.football_data_api_key.strip()

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def _headers(self, deep: bool = False) -> dict[str, str]:
        if not self.configured:
            raise ProviderConfigurationError('FOOTBALL_DATA_API_KEY is not configured.')
        headers = {'X-Auth-Token': self.token}
        if deep:
            headers.update({
                'X-Unfold-Lineups': 'true',
                'X-Unfold-Bookings': 'true',
                'X-Unfold-Subs': 'true',
                'X-Unfold-Goals': 'true',
            })
        return headers

    async def _request_once(self, client: httpx.AsyncClient, path: str, params: dict[str, Any] | None, deep: bool) -> httpx.Response:
        await provider_quota.acquire()
        return await client.get(f'{self.base_url}{path}', headers=self._headers(deep), params=params)

    async def _get(self, path: str, params: dict[str, Any] | None = None, deep: bool = False) -> dict[str, Any]:
        timeout = httpx.Timeout(settings.provider_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = None
            use_deep = deep
            for attempt in range(3):
                response = await self._request_once(client, path, params, use_deep)
                # Some plans expose fixtures/tables but not unfolded deep fields. Retry basic data once.
                if use_deep and response.status_code in {400, 402, 403}:
                    use_deep = False
                    response = await self._request_once(client, path, params, False)
                if response.status_code == 429:
                    retry_after = min(float(response.headers.get('Retry-After', '2') or 2), 10.0)
                    if attempt < 2:
                        await asyncio.sleep(retry_after)
                        continue
                if response.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                response.raise_for_status()
                return response.json()
            assert response is not None
            response.raise_for_status()
            return response.json()

    async def live_matches(self, competitions: list[str] | None = None) -> list[dict]:
        competitions = competitions or settings.competition_codes
        data = await self._get('/matches', {'competitions': ','.join(competitions), 'status': 'LIVE'}, deep=True)
        return [self.normalize_match(m, detailed=True) for m in data.get('matches', [])]

    async def upcoming_matches(self, competitions: list[str] | None = None, days: int | None = None) -> list[dict]:
        competitions = competitions or settings.competition_codes
        days = days or settings.upcoming_days
        today = date.today()
        data = await self._get('/matches', {
            'competitions': ','.join(competitions),
            'dateFrom': today.isoformat(),
            # football-data.org treats dateTo as exclusive; add one day so the final requested day is included.
            'dateTo': (today + timedelta(days=days + 1)).isoformat(),
        })
        matches = [self.normalize_match(m) for m in data.get('matches', [])]
        return [m for m in matches if m.get('status') in {'SCHEDULED', 'TIMED'}]

    async def recent_matches(self, competition: str, days: int = 45) -> list[dict]:
        today = date.today()
        data = await self._get(f'/competitions/{competition}/matches', {
            'dateFrom': (today - timedelta(days=days)).isoformat(),
            # Include matches from today as well; dateTo is exclusive.
            'dateTo': (today + timedelta(days=1)).isoformat(),
            'status': 'FINISHED',
        }, deep=True)
        return [self.normalize_match(m, detailed=True) for m in data.get('matches', [])][-20:][::-1]

    async def match_detail(self, match_id: int) -> dict:
        data = await self._get(f'/matches/{match_id}', deep=True)
        return self.normalize_match(data, detailed=True)

    async def standings(self, competition: str) -> dict:
        data = await self._get(f'/competitions/{competition}/standings')
        tables = []
        for standing in data.get('standings', []):
            if standing.get('type') != 'TOTAL':
                continue
            tables.append({
                'stage': standing.get('stage'),
                'group': standing.get('group'),
                'table': [self.normalize_table_row(row) for row in standing.get('table', [])],
            })
        return {'competition': self.normalize_competition(data.get('competition') or {}), 'standings': tables}

    async def scorers(self, competition: str, limit: int = 16) -> dict:
        data = await self._get(f'/competitions/{competition}/scorers', {'limit': limit})
        return {
            'competition': self.normalize_competition(data.get('competition') or {}),
            'scorers': [
                {
                    'player': {
                        'id': str((s.get('player') or {}).get('id')),
                        'name': (s.get('player') or {}).get('name'),
                        'position': (s.get('player') or {}).get('position'),
                        'nationality': (s.get('player') or {}).get('nationality'),
                    },
                    'team': self.normalize_team(s.get('team') or {}),
                    'goals': s.get('goals') or 0,
                    'assists': s.get('assists'),
                    'penalties': s.get('penalties'),
                    'played_matches': s.get('playedMatches'),
                }
                for s in data.get('scorers', [])
            ],
        }

    async def competition_teams(self, competition: str) -> list[dict]:
        data = await self._get(f'/competitions/{competition}/teams')
        return [self.normalize_team(t, detailed=True) for t in data.get('teams', [])]

    async def team_detail(self, team_id: int) -> dict:
        data = await self._get(f'/teams/{team_id}')
        return self.normalize_team(data, detailed=True)

    @staticmethod
    def normalize_competition(c: dict) -> dict:
        return {
            'id': str(c.get('id')) if c.get('id') is not None else None,
            'code': c.get('code'),
            'name': c.get('name'),
            'emblem': c.get('emblem') if settings.crest_policy == 'provider' else None,
        }

    @staticmethod
    def normalize_player(p: dict) -> dict:
        return {
            'id': str(p.get('id')) if p.get('id') is not None else '',
            'name': p.get('name'),
            'position': p.get('position'),
            'shirt_number': p.get('shirtNumber'),
            'nationality': p.get('nationality'),
            'date_of_birth': p.get('dateOfBirth'),
        }

    @classmethod
    def normalize_team(cls, t: dict, detailed: bool = False) -> dict:
        result = {
            'id': str(t.get('id')) if t.get('id') is not None else '',
            'name': t.get('name'),
            'short_name': t.get('shortName'),
            'tla': t.get('tla'),
            'crest': t.get('crest') if settings.crest_policy == 'provider' else None,
        }
        if detailed:
            website = t.get('website')
            if website and not str(website).lower().startswith(('http://', 'https://')):
                website = None
            result.update({
                'venue': t.get('venue'),
                'founded': t.get('founded'),
                'club_colors': t.get('clubColors'),
                'website': website,
                'coach': (t.get('coach') or {}).get('name'),
                'squad': [cls.normalize_player(p) for p in t.get('squad', [])],
            })
        return result

    @classmethod
    def normalize_lineup(cls, team: dict) -> dict:
        return {
            'formation': team.get('formation'),
            'coach': (team.get('coach') or {}).get('name'),
            'lineup': [cls.normalize_player(p) for p in team.get('lineup', [])],
            'bench': [cls.normalize_player(p) for p in team.get('bench', [])],
        }

    @classmethod
    def normalize_goal(cls, g: dict) -> dict:
        return {
            'minute': g.get('minute'),
            'injury_time': g.get('injuryTime'),
            'type': g.get('type'),
            'team': cls.normalize_team(g.get('team') or {}),
            'scorer': cls.normalize_player(g.get('scorer') or {}),
            'assist': cls.normalize_player(g.get('assist') or {}) if g.get('assist') else None,
            'score': {'home': (g.get('score') or {}).get('home'), 'away': (g.get('score') or {}).get('away')},
        }

    @classmethod
    def normalize_booking(cls, b: dict) -> dict:
        return {
            'minute': b.get('minute'),
            'team': cls.normalize_team(b.get('team') or {}),
            'player': cls.normalize_player(b.get('player') or {}),
            'card': b.get('card'),
        }

    @classmethod
    def normalize_substitution(cls, s: dict) -> dict:
        return {
            'minute': s.get('minute'),
            'team': cls.normalize_team(s.get('team') or {}),
            'player_out': cls.normalize_player(s.get('playerOut') or {}),
            'player_in': cls.normalize_player(s.get('playerIn') or {}),
        }

    @classmethod
    def build_timeline(cls, goals: list[dict], bookings: list[dict], substitutions: list[dict]) -> list[dict]:
        events: list[dict] = []
        for g in goals:
            events.append({
                'minute': g.get('minute'), 'kind': 'goal', 'team': g.get('team'),
                'primary': g.get('scorer'), 'secondary': g.get('assist'), 'meta': g.get('type'), 'score': g.get('score'),
            })
        for b in bookings:
            events.append({
                'minute': b.get('minute'), 'kind': 'booking', 'team': b.get('team'),
                'primary': b.get('player'), 'secondary': None, 'meta': b.get('card'), 'score': None,
            })
        for s in substitutions:
            events.append({
                'minute': s.get('minute'), 'kind': 'substitution', 'team': s.get('team'),
                'primary': s.get('player_in'), 'secondary': s.get('player_out'), 'meta': 'IN_FOR_OUT', 'score': None,
            })
        return sorted(events, key=lambda e: (e.get('minute') or 0), reverse=True)

    @classmethod
    def normalize_match(cls, m: dict, detailed: bool = False) -> dict:
        score = m.get('score') or {}
        full = score.get('fullTime') or {}
        regular = score.get('regularTime') or {}
        extra = score.get('extraTime') or {}
        penalties = score.get('penalties') or {}
        half = score.get('halfTime') or {}
        home = m.get('homeTeam') or {}
        away = m.get('awayTeam') or {}
        result = {
            'id': str(m.get('id')),
            'utc_date': m.get('utcDate'),
            'status': m.get('status'),
            'minute': m.get('minute'),
            'injury_time': m.get('injuryTime'),
            'venue': m.get('venue'),
            'attendance': m.get('attendance'),
            'competition': cls.normalize_competition(m.get('competition') or {}),
            'home_team': cls.normalize_team(home),
            'away_team': cls.normalize_team(away),
            'score': {
                'home': full.get('home'), 'away': full.get('away'),
                'half_home': half.get('home'), 'half_away': half.get('away'),
                'regular_home': regular.get('home'), 'regular_away': regular.get('away'),
                'extra_home': extra.get('home'), 'extra_away': extra.get('away'),
                'penalty_home': penalties.get('home'), 'penalty_away': penalties.get('away'),
                'winner': score.get('winner'), 'duration': score.get('duration'),
            },
            'matchday': m.get('matchday'),
            'stage': m.get('stage'),
            'last_updated': m.get('lastUpdated'),
        }
        if detailed:
            home_lineup = cls.normalize_lineup(home)
            away_lineup = cls.normalize_lineup(away)
            goals = [cls.normalize_goal(g) for g in m.get('goals', [])]
            bookings = [cls.normalize_booking(b) for b in m.get('bookings', [])]
            substitutions = [cls.normalize_substitution(s) for s in m.get('substitutions', [])]
            # Goal/card/substitution payloads may only contain player id + name.
            # Enrich shirt numbers from unfolded lineups when both are available.
            lineup_players = home_lineup['lineup'] + home_lineup['bench'] + away_lineup['lineup'] + away_lineup['bench']
            number_by_id = {p['id']: p.get('shirt_number') for p in lineup_players if p.get('id')}
            def enrich(player):
                if player and not player.get('shirt_number') and player.get('id') in number_by_id:
                    player['shirt_number'] = number_by_id[player['id']]
                return player
            for goal in goals:
                enrich(goal.get('scorer'))
                enrich(goal.get('assist'))
            for booking in bookings:
                enrich(booking.get('player'))
            for sub in substitutions:
                enrich(sub.get('player_out'))
                enrich(sub.get('player_in'))
            result.update({
                'home_lineup': home_lineup,
                'away_lineup': away_lineup,
                'goals': goals,
                'bookings': bookings,
                'substitutions': substitutions,
                'timeline': cls.build_timeline(goals, bookings, substitutions),
                'referees': [
                    {'name': r.get('name'), 'nationality': r.get('nationality'), 'type': r.get('type')}
                    for r in m.get('referees', [])
                ],
                'deep_data_available': bool(
                    home_lineup['lineup'] or away_lineup['lineup'] or goals or bookings or substitutions
                ),
            })
        return result

    @classmethod
    def normalize_table_row(cls, row: dict) -> dict:
        return {
            'position': row.get('position'),
            'team': cls.normalize_team(row.get('team') or {}),
            'played': row.get('playedGames'),
            'won': row.get('won'),
            'draw': row.get('draw'),
            'lost': row.get('lost'),
            'gf': row.get('goalsFor'),
            'ga': row.get('goalsAgainst'),
            'gd': row.get('goalDifference'),
            'points': row.get('points'),
        }


provider = FootballDataProvider()
