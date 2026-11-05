from app.providers.football_data import FootballDataProvider


def test_match_normalization_builds_identified_timeline():
    raw = {
        'id': 99, 'status': 'FINISHED', 'utcDate': '2026-11-01T12:00:00Z',
        'competition': {'id': 1, 'code': 'PL', 'name': 'Premier League'},
        'homeTeam': {
            'id': 10, 'name': 'Home FC', 'shortName': 'Home',
            'formation': '4-3-3',
            'lineup': [{'id': 101, 'name': 'Alex Nine', 'position': 'Centre-Forward', 'shirtNumber': 9}],
            'bench': [],
        },
        'awayTeam': {'id': 20, 'name': 'Away FC', 'shortName': 'Away', 'formation': '4-4-2', 'lineup': [], 'bench': []},
        'score': {'fullTime': {'home': 1, 'away': 0}, 'halfTime': {'home': 0, 'away': 0}},
        'goals': [{'minute': 55, 'team': {'id':10,'name':'Home FC'}, 'scorer': {'id':101,'name':'Alex Nine'}, 'assist': None, 'score': {'home':1,'away':0}}],
        'bookings': [], 'substitutions': [],
    }
    match = FootballDataProvider.normalize_match(raw, detailed=True)
    assert match['score']['home'] == 1
    assert match['goals'][0]['scorer']['shirt_number'] == 9
    assert match['timeline'][0]['kind'] == 'goal'
    assert match['timeline'][0]['primary']['name'] == 'Alex Nine'


def test_match_normalization_preserves_knockout_score_context():
    raw = {
        'id': 100,
        'status': 'FINISHED',
        'utcDate': '2026-11-02T20:00:00Z',
        'competition': {'id': 2, 'code': 'CL', 'name': 'Champions League'},
        'homeTeam': {'id': 1, 'name': 'Home FC'},
        'awayTeam': {'id': 2, 'name': 'Away FC'},
        'score': {
            'winner': 'HOME_TEAM',
            'duration': 'PENALTY_SHOOTOUT',
            'fullTime': {'home': 1, 'away': 1},
            'regularTime': {'home': 1, 'away': 1},
            'extraTime': {'home': 0, 'away': 0},
            'penalties': {'home': 5, 'away': 4},
            'halfTime': {'home': 0, 'away': 0},
        },
    }
    match = FootballDataProvider.normalize_match(raw)
    assert match['score']['home'] == 1
    assert match['score']['away'] == 1
    assert match['score']['penalty_home'] == 5
    assert match['score']['penalty_away'] == 4
    assert match['score']['duration'] == 'PENALTY_SHOOTOUT'
    assert match['score']['winner'] == 'HOME_TEAM'


def test_team_detail_rejects_non_http_website_urls():
    team = FootballDataProvider.normalize_team(
        {'id': 7, 'name': 'Safe FC', 'website': 'javascript:alert(1)', 'squad': []},
        detailed=True,
    )
    assert team['website'] is None
