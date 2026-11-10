# NextBook

A private, AI-powered tracker for book series. Log your cliffhangers and thoughts
when you finish a book, see a countdown to the next release, and get a personal
"Previously on..." recap generated from your own notes when the sequel comes out.

**Stack:** Python, Flask, SQLite (SQLAlchemy), Flask-Login, Flask-WTF, Bootstrap 5,
Google Books API, Google Gemini API, AWS EC2.

## Features

- Account registration and login (hashed passwords, CSRF-protected forms)
- Book search through the Google Books API, with a 24-hour local cache
- A personal bookshelf with series number, total books and next release date
- Live countdown to the next book in a series
- Private notes per book, with a "cliffhanger" flag (create, edit, delete)
- AI recap: Gemini writes a short, spoiler-free reminder using only the user's notes

## Run locally (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then open .env and fill in your keys
python run.py
```

Open http://127.0.0.1:5000 in your browser.

On macOS / Linux use `python3`, `source venv/bin/activate` and `cp` instead.

## Project structure

```
nextbook/
├── app/
│   ├── __init__.py          # app factory, database, login manager, CSRF
│   ├── models.py            # User, Book, Note, ApiCache tables
│   ├── forms.py             # form validation
│   ├── auth.py              # register, login, logout
│   ├── main.py              # landing page and bookshelf
│   ├── books.py             # search, book page, series info, notes, recap
│   ├── services/
│   │   ├── google_books.py  # Google Books API client with cache
│   │   └── gemini.py        # Gemini API client and prompt
│   ├── templates/           # HTML (Jinja2)
│   └── static/              # CSS, fonts, Bootstrap (served locally)
├── config.py                # settings, reads secrets from .env
├── run.py                   # development entry point
└── requirements.txt
```

## Privacy

Every book and note is tied to the logged-in user's id, and every database query
checks that id. Opening another user's book or note returns "404 Not Found".
To write a recap, only the book's title, author and the user's notes for that book
are sent to Gemini.
