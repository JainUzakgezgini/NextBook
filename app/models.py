import hashlib
import hmac
from datetime import date, datetime, timezone

from flask import current_app
from flask_login import UserMixin
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    books = db.relationship("Book", backref="owner", lazy=True, cascade="all, delete-orphan")
    notes = db.relationship("Note", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Login sessions and password reset -------------------------------------
    # The "stamp" is a short fingerprint of the password hash (made with the secret key,
    # so it reveals nothing about the password). When the password changes, the stamp
    # changes, and that automatically:
    #   - logs the account out on every device (old login cookies stop matching)
    #   - makes every earlier reset link stop working (each link works only once)

    def auth_stamp(self):
        key = current_app.config["SECRET_KEY"].encode()
        return hmac.new(key, self.password_hash.encode(), hashlib.sha256).hexdigest()[:20]

    def get_id(self):
        return f"{self.id}:{self.auth_stamp()}"

    def make_reset_token(self):
        return _reset_serializer().dumps({"user": self.id, "stamp": self.auth_stamp()})

    @staticmethod
    def from_reset_token(token):
        """Return the user for a valid, unexpired, unused reset token, otherwise None."""
        try:
            data = _reset_serializer().loads(token, max_age=current_app.config["PASSWORD_RESET_MAX_AGE"])
            user = db.session.get(User, int(data["user"]))
        except (BadSignature, KeyError, TypeError, ValueError):
            return None  # forged, damaged or expired (SignatureExpired is a BadSignature)
        if user is None or not hmac.compare_digest(str(data.get("stamp")), user.auth_stamp()):
            return None  # password already changed since the link was made
        return user


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="nextbook-password-reset")


class Book(db.Model):
    """A book on one user's private shelf."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    # Metadata from Google Books
    google_id = db.Column(db.String(40), index=True)
    title = db.Column(db.String(300), nullable=False)
    authors = db.Column(db.String(300))
    thumbnail_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    published_date = db.Column(db.String(20))
    page_count = db.Column(db.Integer)
    average_rating = db.Column(db.Float)
    ratings_count = db.Column(db.Integer)

    # Series info: Google Books is unreliable here, so the user can edit all of it
    series_name = db.Column(db.String(200))
    series_index = db.Column(db.Integer)
    total_books_in_series = db.Column(db.Integer)
    next_release_date = db.Column(db.Date)  # drives the countdown

    # Last AI recap, stored so we don't spend API quota on every page view
    recap_text = db.Column(db.Text)
    recap_created_at = db.Column(db.DateTime(timezone=True))

    added_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    notes = db.relationship(
        "Note", backref="book", lazy=True, cascade="all, delete-orphan", order_by="Note.created_at.desc()"
    )

    @property
    def days_until_release(self):
        if not self.next_release_date:
            return None
        return (self.next_release_date - date.today()).days


class Note(db.Model):
    """A private note or cliffhanger log, visible only to its owner."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_cliffhanger = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True))


class ApiCache(db.Model):
    """Local cache for Google Books responses, to avoid repeating the same API calls."""

    key = db.Column(db.String(300), primary_key=True)
    payload = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime(timezone=True), default=utcnow)


@login_manager.user_loader
def load_user(session_id):
    user_id, _, stamp = (session_id or "").partition(":")
    if not user_id.isdigit() or not stamp:
        return None  # old-style cookie from before this update: log in again
    user = db.session.get(User, int(user_id))
    if user is None or not hmac.compare_digest(stamp, user.auth_stamp()):
        return None  # password was changed: this login is no longer valid
    return user
