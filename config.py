import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = os.environ.get("CODEC_DATABASE_PATH", str(BASE_DIR / "codec.db"))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "codec-tactical-mission-control-key-14085")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    DEBUG = True
