import os
from datetime import date

from flask import Flask, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import INSECURE_DEFAULT_KEY, Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)  # limits are set per route

login_manager.login_view = "auth.login"
login_manager.login_message = "Log in to see your private shelf."
login_manager.login_message_category = "info"

# Colors for books that have no cover image (picked by book id, so they stay the same)
SPINE_COLORS = ["#7B2D26", "#1F4A3C", "#2E3F5C", "#8C6A2F", "#5A3B5C", "#3F5A4B", "#6E4A2E"]

# Content Security Policy: the browser only runs scripts, styles and fonts from our own
# site, and only shows images from our site and Google Books. If someone ever managed to
# put a <script> into a page, the browser would refuse to run it.
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",  # small inline style="" attributes on book spines
    "img-src 'self' data: https://books.google.com https://*.googleusercontent.com",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

ERROR_TEXT = {
    400: ("Something was wrong with that request", "The form may have expired. Go back, reload the page and try again."),
    404: ("Page not found", "This page doesn't exist, or it belongs to someone else's private shelf."),
    413: ("That was too much text", "Shorten what you wrote and try again."),
    429: ("Too many attempts", "You did that too often in a short time. Wait a few minutes, then try again."),
    500: ("Something went wrong on our side", "Try again in a moment. If it keeps happening, the problem is ours, not yours."),
}


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Refuse to run the live (HTTPS) site with the example secret key or a short one:
    # anyone who knows the key could forge login cookies and reset links.
    if app.config.get("SESSION_COOKIE_SECURE") and (
        app.config["SECRET_KEY"] == INSECURE_DEFAULT_KEY or len(app.config["SECRET_KEY"]) < 32
    ):
        raise RuntimeError("Set a long random SECRET_KEY in .env before running the live site.")

    if app.config.get("BEHIND_PROXY"):
        # Trust exactly one proxy (our Nginx) for the visitor's IP address and for "https".
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    os.makedirs(os.path.join(os.path.dirname(app.root_path), "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.auth import bp as auth_bp
    from app.books import bp as books_bp
    from app.main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(books_bp)

    @app.after_request
    def security_headers(response):
        h = response.headers
        h.setdefault("Content-Security-Policy", CSP)
        h.setdefault("X-Content-Type-Options", "nosniff")         # don't guess file types
        h.setdefault("X-Frame-Options", "DENY")                   # no embedding in other sites (clickjacking)
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.is_secure:
            h.setdefault("Strict-Transport-Security", "max-age=31536000")  # always use HTTPS from now on
        # Private pages must not be stored by the browser or shown again with the Back button
        # after logging out (for example on a shared computer).
        if current_user.is_authenticated and not request.path.startswith("/static/"):
            h["Cache-Control"] = "no-store"
        return response

    def error_page(code):
        title, text = ERROR_TEXT[code]
        return render_template("error.html", code=code, title=title, text=text), code

    for code in (400, 404, 413, 429, 500):
        app.register_error_handler(code, lambda e, c=code: error_page(c))
    app.register_error_handler(CSRFError, lambda e: error_page(400))

    @app.context_processor
    def helpers():
        return {"today": date.today()}

    @app.template_filter("spine_color")
    def spine_color(book_id):
        return SPINE_COLORS[(book_id or 0) % len(SPINE_COLORS)]

    @app.template_filter("year")
    def year(published_date):
        return (published_date or "")[:4]

    with app.app_context():
        from app import models  # noqa: F401  (registers the tables)
        db.create_all()

    return app
