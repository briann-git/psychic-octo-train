from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    odds_api_key: str                   # required — no default
    db_path: str = "ledger.db"
    supported_leagues: list[str] = ["PL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"]
    confidence_threshold: float = 0.60
    min_lead_hours: int = 2
    max_lead_hours: int = 48
    flat_stake: float = 10.0
    log_level: str = "INFO"
    csv_cache_dir: str = ".csv_cache"
    csv_max_age_hours: int = 24

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
