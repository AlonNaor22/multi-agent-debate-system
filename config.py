from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    model_name: str = "claude-sonnet-4-6"
    temperature_debaters: float = 0.7
    temperature_judge: float = 0.3
    max_tokens: int = 1024
    num_rebuttal_rounds: int = 2
    # Resilience for the LLM calls (see src/agents/base_agent.py).
    # request_timeout is seconds per request; max_retries is how many times the
    # Anthropic SDK retries transient failures (429 / 5xx / connection) with
    # exponential backoff before giving up.
    request_timeout: float = 60.0
    max_retries: int = 2
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]
    available_styles: list[str] = ["passionate", "aggressive", "academic", "humorous"]
    default_pro_style: str = "passionate"
    default_con_style: str = "passionate"
    # Where completed debates are persisted (see api/db.py). A local SQLite file
    # by default; override with the DATABASE_URL env var for another backend.
    database_url: str = "sqlite:///./debates.db"


settings = Settings()

# Re-export as module-level names so all existing imports work unchanged
MODEL_NAME = settings.model_name
TEMPERATURE_DEBATERS = settings.temperature_debaters
TEMPERATURE_JUDGE = settings.temperature_judge
MAX_TOKENS = settings.max_tokens
NUM_REBUTTAL_ROUNDS = settings.num_rebuttal_rounds
REQUEST_TIMEOUT = settings.request_timeout
MAX_RETRIES = settings.max_retries
CORS_ORIGINS = settings.cors_origins
AVAILABLE_STYLES = settings.available_styles
DEFAULT_PRO_STYLE = settings.default_pro_style
DEFAULT_CON_STYLE = settings.default_con_style
DATABASE_URL = settings.database_url
