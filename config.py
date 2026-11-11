import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL")  # optional, see app/services/gemini.py
    GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY")  # optional

    # SQLite file lives in the instance/ folder (ignored by Git).
    # An absolute path avoids "works locally, breaks on the server" path bugs.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "nextbook.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cookies: never readable by JavaScript, not sent with cross-site requests.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # On the HTTPS server set COOKIE_SECURE=1 in .env, so login cookies are only sent over HTTPS.
    # Leave it off locally (http://127.0.0.1), otherwise logging in won't work.
    SESSION_COOKIE_SECURE = REMEMBER_COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
