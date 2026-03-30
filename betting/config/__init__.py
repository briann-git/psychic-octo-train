from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    odds_api_key: str                   # required — no default
    db_path: str = "ledger.db"
    confidence_threshold: float = 0.60
    min_lead_hours: int = 2
    max_lead_hours: int = 48
    flat_stake: float = 10.0
    log_level: str = "INFO"
    csv_cache_dir: str = ".csv_cache"
    csv_max_age_hours: int = 24
    agent_weights: dict[str, float] = Field(
        default={"statistical": 0.60, "market": 0.40}
    )
    paper_trading: bool = True    # default safe — flip to false when ready to place real bets

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
