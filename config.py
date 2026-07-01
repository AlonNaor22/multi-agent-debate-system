from typing import Annotated

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    model_name: str = "claude-sonnet-4-6"
    temperature_debaters: float = 0.7
    temperature_judge: float = 0.3
    max_tokens: int = 1024
    # The judge's structured scoreboard (src/scoring.py) must score every
    # argument from both sides in one JSON response, which needs far more
    # headroom than a single debate turn — a multi-round debate can easily
    # exceed max_tokens above and get truncated mid-JSON, failing schema
    # validation. Kept separate so raising it doesn't also inflate (and slow
    # down) every ordinary turn.
    scoring_max_tokens: int = 4096
    num_rebuttal_rounds: int = 2
    # Live in-memory debate sessions are held per-process (single uvicorn worker —
    # see api.services.debate_service). Cap how many can exist at once so a flood
    # of POST /api/debates calls that never open a WebSocket can't exhaust memory;
    # the create endpoint returns HTTP 429 once this many are live.
    max_live_sessions: int = 100
    # A session created via POST but never driven by a WebSocket is an orphan; a
    # background sweeper evicts orphans whose age exceeds this many seconds. A
    # live debate (a socket is driving it) is never swept, so this can sit well
    # below a debate's natural length.
    session_ttl_seconds: float = 900.0
    # How often (seconds) the background sweeper wakes to evict expired orphans.
    session_sweep_interval_seconds: float = 60.0
    # Resilience for the LLM calls (see src/agents/base_agent.py).
    # request_timeout is seconds per request; max_retries is how many times the
    # Anthropic SDK retries transient failures (429 / 5xx / connection) with
    # exponential backoff before giving up.
    request_timeout: float = 60.0
    max_retries: int = 2
    # The single source of truth for allowed CORS origins (used by api/main.py):
    # the Vite dev server, its preview server, and the 127.0.0.1 alias of the dev
    # server. ``NoDecode`` opts this list out of pydantic-settings' default JSON
    # parsing so CORS_ORIGINS can be given as a friendly comma-separated string
    # (split by the validator below) rather than a JSON array.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
    ]
    # NoDecode (as with cors_origins) lets AVAILABLE_STYLES be supplied as a
    # comma-separated env string rather than a JSON array.
    available_styles: Annotated[list[str], NoDecode] = [
        "passionate",
        "aggressive",
        "academic",
        "humorous",
    ]
    default_pro_style: str = "passionate"
    default_con_style: str = "passionate"
    # Where completed debates are persisted (see api/db.py). A local SQLite file
    # by default; override with the DATABASE_URL env var for another backend.
    database_url: str = "sqlite:///./debates.db"

    @field_validator("cors_origins", "available_styles", mode="before")
    @classmethod
    def _split_comma_separated_list(cls, value: object) -> object:
        """Accept these list settings as a comma-separated string as well as a list.

        Pairs with their ``NoDecode`` annotations: pydantic-settings would
        otherwise require a JSON array in the env var and raise on a plain
        comma-separated string.
        """
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


settings = Settings()

# Re-export as module-level names so all existing imports work unchanged
MODEL_NAME = settings.model_name
TEMPERATURE_DEBATERS = settings.temperature_debaters
TEMPERATURE_JUDGE = settings.temperature_judge
MAX_TOKENS = settings.max_tokens
SCORING_MAX_TOKENS = settings.scoring_max_tokens
NUM_REBUTTAL_ROUNDS = settings.num_rebuttal_rounds
MAX_LIVE_SESSIONS = settings.max_live_sessions
SESSION_TTL_SECONDS = settings.session_ttl_seconds
SESSION_SWEEP_INTERVAL_SECONDS = settings.session_sweep_interval_seconds
REQUEST_TIMEOUT = settings.request_timeout
MAX_RETRIES = settings.max_retries
CORS_ORIGINS = settings.cors_origins
AVAILABLE_STYLES = settings.available_styles
DEFAULT_PRO_STYLE = settings.default_pro_style
DEFAULT_CON_STYLE = settings.default_con_style
DATABASE_URL = settings.database_url
