from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)

    app_env: str = 'development'
    app_name: str = 'Soccer Intelligence Platform'
    api_v1_prefix: str = '/api/v1'
    frontend_origin: str = 'http://localhost:5173'
    trusted_hosts: str = 'localhost,127.0.0.1'
    trust_proxy_headers: bool = False

    database_url: str = 'sqlite+aiosqlite:///./soccer_intelligence.db'
    redis_url: str = 'redis://localhost:6379/0'

    jwt_secret: str = 'dev-only-change-me'
    jwt_algorithm: str = 'HS256'
    jwt_issuer: str = 'soccer-intelligence-platform'
    jwt_audience: str = 'soccer-intelligence-web'
    access_token_minutes: int = 120

    football_data_api_key: str = ''
    football_data_base_url: str = 'https://api.football-data.org/v4'
    default_competitions: str = 'PL,CL,PD,BL1,SA,FL1'
    live_poll_seconds: int = 30
    upcoming_days: int = 7
    provider_rpm_budget: int = Field(default=8, ge=1, le=10)
    provider_timeout_seconds: float = Field(default=20.0, ge=2, le=60)
    crest_policy: str = 'provider'  # provider | initials

    snapshot_retention_days: int = Field(default=14, ge=1, le=365)
    demo_session_ttl_seconds: int = Field(default=3600, ge=300, le=86400)

    openai_api_key: str = ''
    openai_model: str = 'gpt-6-luna'
    enable_llm_analyst: bool = False

    xg_model_path: str = 'models/xg_model.joblib'
    xg_model_card_path: str = 'models/xg_model_card.json'

    @property
    def competition_codes(self) -> list[str]:
        return [x.strip().upper() for x in self.default_competitions.split(',') if x.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [x.strip() for x in self.trusted_hosts.split(',') if x.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == 'production'

    @model_validator(mode='after')
    def validate_production_secrets(self):
        if self.crest_policy not in {'provider', 'initials'}:
            raise ValueError('CREST_POLICY must be provider or initials')
        if self.is_production:
            weak = {'', 'dev-only-change-me', 'change-this-in-production'}
            if self.jwt_secret in weak or len(self.jwt_secret) < 32 or 'REPLACE_' in self.jwt_secret:
                raise ValueError('Production requires a strong JWT_SECRET of at least 32 characters.')
            if self.frontend_origin.startswith('http://localhost') or 'example.com' in self.frontend_origin:
                raise ValueError('Production FRONTEND_ORIGIN must be the real HTTPS deployment origin.')
            if not self.frontend_origin.startswith('https://'):
                raise ValueError('Production FRONTEND_ORIGIN must use HTTPS.')
            if 'example.com' in self.trusted_hosts:
                raise ValueError('Production TRUSTED_HOSTS must contain the real deployment hostname.')
            if 'REPLACE_' in self.database_url or 'REPLACE_' in self.redis_url:
                raise ValueError('Production database/Redis URLs still contain placeholder credentials.')
            if self.football_data_api_key.strip().upper() == 'REPLACE_ME':
                raise ValueError('FOOTBALL_DATA_API_KEY still contains the production template placeholder.')
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
