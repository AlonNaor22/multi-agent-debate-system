from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    model_name: str = "claude-sonnet-4-6"
    temperature_debaters: float = 0.7
    temperature_judge: float = 0.3
    max_tokens: int = 1024
    num_rebuttal_rounds: int = 2
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]
    available_styles: list[str] = ["passionate", "aggressive", "academic", "humorous"]
    default_pro_style: str = "passionate"
    default_con_style: str = "passionate"


settings = Settings()

# Re-export as module-level names so all existing imports work unchanged
MODEL_NAME = settings.model_name
TEMPERATURE_DEBATERS = settings.temperature_debaters
TEMPERATURE_JUDGE = settings.temperature_judge
MAX_TOKENS = settings.max_tokens
NUM_REBUTTAL_ROUNDS = settings.num_rebuttal_rounds
CORS_ORIGINS = settings.cors_origins
AVAILABLE_STYLES = settings.available_styles
DEFAULT_PRO_STYLE = settings.default_pro_style
DEFAULT_CON_STYLE = settings.default_con_style
