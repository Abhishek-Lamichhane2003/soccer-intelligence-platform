from app.services.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.services.demo import DemoMatchEngine
from app.services.xg import shot_geometry, xg_service


def test_jwt_round_trip_has_audience_and_issuer_validation():
    token = create_access_token('42')
    payload = decode_access_token(token)
    assert payload['sub'] == '42'
    assert payload['iss']
    assert payload['aud']


def test_demo_engines_do_not_share_mutable_state():
    a = DemoMatchEngine(seed=1)
    b = DemoMatchEngine(seed=2)
    a.home_score = 99
    assert b.home_score == 2


def test_shot_geometry_rewards_central_close_shots():
    close_distance, close_angle = shot_geometry(114, 40)
    far_distance, far_angle = shot_geometry(80, 10)
    assert close_distance < far_distance
    assert close_angle > far_angle
    assert xg_service.predict({'x':114,'y':40})['xg'] > xg_service.predict({'x':80,'y':10})['xg']


def test_password_hashing_handles_long_unicode_passwords():
    password = '⚽' * 80 + '-portfolio-password'
    digest = hash_password(password)
    assert verify_password(password, digest) is True
    assert verify_password(password + 'x', digest) is False


def test_production_settings_reject_template_placeholders():
    import pytest
    from app.core.config import Settings

    with pytest.raises(ValueError):
        Settings(
            app_env='production',
            jwt_secret='x' * 64,
            frontend_origin='https://soccer.example.com',
            trusted_hosts='soccer.example.com',
            database_url='postgresql+asyncpg://user:REPLACE_WITH_PASSWORD@postgres/db',
            redis_url='redis://:REPLACE_WITH_PASSWORD@redis:6379/0',
        )
