import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = os.environ.get("CODEC_DATABASE_PATH", str(BASE_DIR / "codec.db"))

def _get_or_create_local_secret() -> str:
    """Generates or loads a persistent local secret key rather than using a static checked-in default."""
    env_secret = os.environ.get("CODEC_SECRET_KEY")
    if env_secret:
        return env_secret
    secret_file = BASE_DIR / ".codec_secret"
    if secret_file.exists():
        try:
            return secret_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    new_secret = secrets.token_hex(32)
    try:
        secret_file.write_text(new_secret, encoding="utf-8")
    except Exception:
        pass
    return new_secret

class Config:
    SECRET_KEY = _get_or_create_local_secret()
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    DEBUG = os.environ.get("CODEC_DEBUG", "False").lower() in ("true", "1", "yes")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    ALLOWED_ORIGINS = [
        "http://127.0.0.1:5050",
        "http://localhost:5050",
        "http://127.0.0.1",
        "http://localhost"
    ]

