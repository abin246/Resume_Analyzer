import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):
        return False


load_dotenv()


def _to_bool(value: str, default: bool = True) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    localai_base_url: str = os.getenv("LOCALAI_BASE_URL", "http://127.0.0.1:8080")
    localai_model: str = os.getenv("LOCALAI_MODEL", "meta-llama-3.1-8b-instruct")
    max_resume_file_size_mb: int = int(os.getenv("MAX_RESUME_FILE_SIZE_MB", "5"))
    enable_fallback_analyzer: bool = _to_bool(
        os.getenv("ENABLE_FALLBACK_ANALYZER", "true"),
        default=True,
    )
    database_path: str = os.getenv("DATABASE_PATH", "data/resume_analyzer.db")
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
    )


settings = Settings()
