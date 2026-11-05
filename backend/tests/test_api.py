from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json()['status'] in {'ok', 'degraded'}


def test_config_shows_truthful_model_and_provider_state():
    with TestClient(app) as client:
        data = client.get('/api/v1/config').json()
        assert data['demo_available'] is True
        assert data['provider'] == 'football-data.org'
        assert 'xg' in data
        assert data['attribution'] == 'Data provided by football-data.org'


def test_live_without_key_is_honest():
    with TestClient(app) as client:
        data = client.get('/api/v1/matches/live').json()
        assert data['configured'] is False
        assert data['matches'] == []


def test_demo_snapshot_has_22_identified_players_and_events():
    with TestClient(app) as client:
        data = client.get('/api/v1/demo/snapshot').json()
        assert data['mode'] == 'demo'
        assert len(data['lineups']['home']['players']) == 11
        assert len(data['lineups']['away']['players']) == 11
        assert all(p['name'] and p['shirt_number'] for p in data['lineups']['home']['players'])
        assert all(p['name'] and p['shirt_number'] for p in data['lineups']['away']['players'])
        goals = [e for e in data['events'] if e['type'] == 'goal']
        assert goals and goals[0]['player'] and goals[0]['shirt_number']


def test_demo_sessions_are_unique():
    with TestClient(app) as client:
        a = client.post('/api/v1/demo/sessions').json()
        b = client.post('/api/v1/demo/sessions').json()
        assert a['session_id'] != b['session_id']
        assert a['snapshot']['mode'] == b['snapshot']['mode'] == 'demo'


def test_xg_endpoint_is_truthfully_labeled():
    with TestClient(app) as client:
        data = client.post('/api/v1/ml/xg/predict', json={'x': 108, 'y': 40, 'body_part': 'Right Foot'}).json()
        assert 0 < data['xg'] < 1
        assert data['model'] in {'geometric-baseline', 'trained-statsbomb-model'}


def test_ml_status_declares_baseline_win_probability():
    with TestClient(app) as client:
        data = client.get('/api/v1/ml/status').json()
        assert data['win_probability']['trained'] is False


def test_cookie_auth_and_favorites_flow():
    with TestClient(app) as client:
        registered = client.post('/api/v1/auth/register', json={'email':'portfolio@example.com','password':'strong-pass-123'})
        assert registered.status_code == 200
        assert 'httponly' in registered.headers.get('set-cookie', '').lower()
        assert 'access_token' not in registered.json()
        me = client.get('/api/v1/auth/me')
        assert me.status_code == 200
        assert me.json()['email'] == 'portfolio@example.com'
        favorite = client.post('/api/v1/favorites', json={'entity_type':'team','entity_id':'57','label':'Example FC'})
        assert favorite.status_code == 200
        listed = client.get('/api/v1/favorites').json()
        assert len(listed) == 1
        assert client.delete(f"/api/v1/favorites/{listed[0]['id']}").status_code == 200
        assert client.post('/api/v1/auth/logout').status_code == 200
        assert client.get('/api/v1/auth/me').status_code == 401


def test_rejects_unknown_competition_before_spending_provider_quota(monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes.provider, 'token', 'test-token')
    with TestClient(app) as client:
        response = client.get('/api/v1/competitions/NOTREAL/standings')
        assert response.status_code == 400
        assert response.json()['detail'] == 'Unsupported competition code.'
