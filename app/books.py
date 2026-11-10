from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.forms import NoteForm, SeriesForm
from app.models import Book, Note
from app.services import gemini, google_books

bp = Blueprint("books", __name__)


def owned_book(book_id):
    """Return the book only if it belongs to the logged-in user. Otherwise 404."""
    book = db.session.get(Book, book_id)
    if book is None or book.user_id != current_user.id:
        abort(404)
    return book


def owned_note(note_id):
    note = db.session.get(Note, note_id)
    if note is None or note.user_id != current_user.id:
        abort(404)
    return note


@bp.route("/search")
@login_required
def search():
    query = request.args.get("q", "").strip()
    results, error = [], None
    if query:
        try:
            results = google_books.search(query)
        except google_books.BooksAPIError as exc:
            error = str(exc)
    on_shelf = {
        gid: bid
        for gid, bid in db.session.execute(
            db.select(Book.google_id, Book.id).filter_by(user_id=current_user.id)
        ).all()
    }
    return render_template("books/search.html", query=query, results=results, error=error, on_shelf=on_shelf)


@bp.route("/books/add", methods=["POST"])
@login_required
def add():
    google_id = request.form.get("google_id", "")
    existing = db.session.scalar(db.select(Book).filter_by(user_id=current_user.id, google_id=google_id))
    if existing:
        return redirect(url_for("books.detail", book_id=existing.id))
    try:
        data = google_books.get_volume(google_id)
    except google_books.BooksAPIError as exc:
        flash(str(exc), "danger")
        return redirect(request.referrer or url_for("books.search"))
    if not data:
        flash("Couldn't find that book on Google Books.", "danger")
        return redirect(url_for("books.search"))

    data.pop("subtitle", None)
    book = Book(user_id=current_user.id, **data)
    db.session.add(book)
    db.session.commit()
    flash(f"“{book.title}” is on your shelf. Add the series info and your first note below.", "success")
    return redirect(url_for("books.detail", book_id=book.id))


@bp.route("/books/<int:book_id>")
@login_required
def detail(book_id):
    book = owned_book(book_id)
    series_form = SeriesForm(obj=book)
    note_form = NoteForm()
    return render_template("books/detail.html", recap=gemini.parse_recap(book.recap_text), book=book, series_form=series_form, note_form=note_form)


@bp.route("/books/<int:book_id>/series", methods=["POST"])
@login_required
def update_series(book_id):
    book = owned_book(book_id)
    form = SeriesForm()
    if form.validate_on_submit():
        book.series_name = (form.series_name.data or "").strip() or None
        book.series_index = form.series_index.data
        book.total_books_in_series = form.total_books_in_series.data
        book.next_release_date = form.next_release_date.data
        db.session.commit()
        flash("Series info saved.", "success")
        return redirect(url_for("books.detail", book_id=book.id))
    return render_template("books/detail.html", recap=gemini.parse_recap(book.recap_text), book=book, series_form=form, note_form=NoteForm()), 400


@bp.route("/books/<int:book_id>/remove", methods=["POST"])
@login_required
def remove(book_id):
    book = owned_book(book_id)
    title = book.title
    db.session.delete(book)
    db.session.commit()
    flash(f"“{title}” and its notes were removed from your shelf.", "info")
    return redirect(url_for("main.dashboard"))


@bp.route("/books/<int:book_id>/notes", methods=["POST"])
@login_required
def add_note(book_id):
    book = owned_book(book_id)
    form = NoteForm()
    if form.validate_on_submit():
        db.session.add(Note(
            user_id=current_user.id, book_id=book.id,
            content=form.content.data.strip(), is_cliffhanger=form.is_cliffhanger.data,
        ))
        db.session.commit()
        flash("Note saved. Only you can see it.", "success")
        return redirect(url_for("books.detail", book_id=book.id, _anchor="notes"))
    return render_template("books/detail.html", recap=gemini.parse_recap(book.recap_text), book=book, series_form=SeriesForm(obj=book), note_form=form), 400


@bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    note = owned_note(note_id)
    form = NoteForm(obj=note)
    if form.validate_on_submit():
        note.content = form.content.data.strip()
        note.is_cliffhanger = form.is_cliffhanger.data
        note.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Note updated.", "success")
        return redirect(url_for("books.detail", book_id=note.book_id, _anchor="notes"))
    return render_template("books/edit_note.html", note=note, form=form)


@bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    note = owned_note(note_id)
    book_id = note.book_id
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted.", "info")
    return redirect(url_for("books.detail", book_id=book_id, _anchor="notes"))


@bp.route("/books/<int:book_id>/recap", methods=["POST"])
@login_required
def recap(book_id):
    book = owned_book(book_id)
    try:
        book.recap_text = gemini.generate_recap(book, book.notes)
        book.recap_created_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Your recap is ready.", "success")
    except gemini.RecapError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("books.detail", book_id=book.id, _anchor="recap"))
