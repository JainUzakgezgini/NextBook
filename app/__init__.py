import os
from datetime import date

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Log in to see your private shelf."
login_manager.login_message_category = "info"

# Colors for books that have no cover image (picked by book id, so they stay the same)
SPINE_COLORS = ["#7B2D26", "#1F4A3C", "#2E3F5C", "#8C6A2F", "#5A3B5C", "#3F5A4B", "#6E4A2E"]


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.join(os.path.dirname(app.root_path), "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.auth import bp as auth_bp
    from app.books import bp as books_bp
    from app.main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(books_bp)

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
