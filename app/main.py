from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Book

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    # Every query is filtered by the logged-in user: nobody can see anyone else's shelf
    books = db.session.scalars(
        db.select(Book).filter_by(user_id=current_user.id).order_by(Book.added_at.desc())
    ).all()
    upcoming = sorted(
        (b for b in books if b.days_until_release is not None and b.days_until_release >= 0),
        key=lambda b: b.days_until_release,
    )
    return render_template("main/dashboard.html", books=books, upcoming=upcoming)
