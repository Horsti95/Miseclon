from pathlib import Path
from pydantic_settings import BaseSettings


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"


class Settings(BaseSettings):
    app_name: str = "Miseclon"
    database_url: str = f"sqlite:///{(DATA_DIR / 'mise.db').as_posix()}"
    host: str = "0.0.0.0"
    port: int = 8000
    default_llm_base_url: str = "http://127.0.0.1:11434/v1"
    default_llm_model: str = "qwen2.5:14b"
    default_llm_api_key: str = "ollama"

    model_config = {
        "env_file": str(ROOT_DIR / ".env"),
        "env_prefix": "MISE_",
        "extra": "ignore",
    }


settings = Settings()
