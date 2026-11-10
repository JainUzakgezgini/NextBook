from datetime import date, datetime, timezone

from flask_login import UserMixin
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
def load_user(user_id):
    return db.session.get(User, int(user_id))
