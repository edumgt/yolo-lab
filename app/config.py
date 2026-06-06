import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# 1) Shared defaults (.env) -> 2) Environment-specific (.env.local/.env.dev/.env.prod)
load_dotenv(BASE_DIR / ".env", override=False)
APP_ENV = os.getenv("APP_ENV", "local").strip().lower() or "local"
load_dotenv(BASE_DIR / f".env.{APP_ENV}", override=True)

# Optional custom env file override
custom_env_file = os.getenv("ENV_FILE", "").strip()
if custom_env_file:
    custom_env_path = Path(custom_env_file)
    if not custom_env_path.is_absolute():
        custom_env_path = BASE_DIR / custom_env_path
    load_dotenv(custom_env_path, override=True)


class Config:
    """Flask app settings."""

    APP_ENV = APP_ENV
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///users.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = os.getenv("SESSION_TYPE", "filesystem")
    SESSION_PERMANENT = False

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
    S3_BUCKET = os.getenv("S3_BUCKET", "my-bucket")

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    RESULT_FOLDER = os.getenv("RESULT_FOLDER", "results")
    SAMPLE_FOLDER = os.getenv("SAMPLE_FOLDER", "samples")

    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))

    _default_debug = APP_ENV != "prod"
    DEBUG = _to_bool(os.getenv("FLASK_DEBUG"), default=_default_debug)
