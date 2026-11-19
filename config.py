import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

INSECURE_DEFAULT_KEY = "dev-only-insecure-key"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", INSECURE_DEFAULT_KEY)
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

    # Reject request bodies over 1 MB (nothing in the app needs more)
    MAX_CONTENT_LENGTH = 1024 * 1024

    # --- Cookies -------------------------------------------------------------
    # Never readable by JavaScript, not sent with cross-site requests.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=14)  # "Keep me logged in" lasts 2 weeks, not 1 year
    # On the HTTPS server set COOKIE_SECURE=1 in .env, so login cookies are only sent over HTTPS.
    # Leave it off locally (http://127.0.0.1), otherwise logging in won't work.
    SESSION_COOKIE_SECURE = REMEMBER_COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"

    # --- Server behind Nginx ---------------------------------------------------
    # On the server set BEHIND_PROXY=1, so the app sees the visitor's real IP address
    # (needed for rate limits) and knows the connection is HTTPS.
    BEHIND_PROXY = os.environ.get("BEHIND_PROXY") == "1"
    # Public address used in password reset e-mails, e.g. https://nextbook.duckdns.org
    # Fixed in config so an attacker can't make the e-mail link point to another site.
    APP_BASE_URL = (os.environ.get("APP_BASE_URL") or "").rstrip("/")

    # --- Rate limits (Flask-Limiter) ---------------------------------------------
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    # --- E-mail (password reset) -------------------------------------------------
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_FROM = os.environ.get("MAIL_FROM") or MAIL_USERNAME
    PASSWORD_RESET_MAX_AGE = 30 * 60  # reset links work for 30 minutes
