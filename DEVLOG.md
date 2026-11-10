# Development log: real problems and solutions

Use this file to write down problems as they happen. They go into the
"Problems & Solutions" sections of the project documentation.

## Implementation

**Problem:** Every search returned "Google Books is getting too many requests" (HTTP 429), even the first one.
**Cause:** Google Books limits requests that are sent without an API key, and the shared keyless quota was used up.
**Solution:** Created a Google Books API key in Google Cloud Console, enabled the Books API,
added the key to `.env` as `GOOGLE_BOOKS_API_KEY`, and made the error message explain this case.

**Problem:** The Google Books API key was in `.env`, but the app still said the key was missing.
**Cause:** The key was written on the line `# GOOGLE_BOOKS_API_KEY=...`. The `#` makes the line a comment, so it was ignored.
**Solution:** Removed the `#`. Checked that the key loads with a one-line test:
`python -c "from config import Config; print(bool(Config.GOOGLE_BOOKS_API_KEY))"`.

**Problem:** The same search with different capital letters or extra spaces could be treated as different searches.
**Solution:** Searches are normalized (lowercase, single spaces) before calling the API and before using the cache.

**Problem:** Registration failed on the first try with an unclear message
("Use letters, numbers, dots, dashes or underscores").
**Cause:** The username contained a character the validator doesn't allow (a space or a Turkish letter).
**Solution:** Rewrote the error message to say exactly what is allowed, and added a hint under the field.

**Problem:** After adding new columns to the Book table, the app kept using the old table.
**Cause:** `db.create_all()` only creates missing tables. It never changes existing ones.
**Solution:** Deleted the local development database (`instance/nextbook.db`) so it was recreated
with the new schema. For a real product, a migration tool such as Flask-Migrate would be used.

**Problem:** Google Books rarely provides series numbers and never knows future release dates.
**Solution:** Series name, book number, total books and next release date are editable by the user.
The countdown is driven by the user's date.

**Problem:** Covers on the bookshelf didn't line up with the shelf plank.
**Cause:** When a label under a book had more lines, flexbox shrank the cover area to make room.
**Solution:** Set `flex-shrink: 0` on the cover area and the label, and made each shelf row taller.

**Problem:** The tilted book in the landing page illustration jumped above the shelf.
**Cause:** CSS rotated it around its top-left corner instead of its bottom edge.
**Solution:** Rotated around the bottom edge using `translateY(50%) rotate(...) translateY(-50%)`.

**Problem:** Fonts and Bootstrap loaded from external CDNs.
**Solution:** Served them locally from `app/static/` so the app works without third-party requests.

**Problem:** Gemini model names change over time, and an old name returns 404.
**Solution:** The app tries a list of models in order, starting with Google's `-latest` aliases.

## Testing & improvement

**Problem:** During testing, the AI recap only repeated the reader's own notes in different words.
It added almost no value, even though generative AI is meant to be a core feature of the app.
**Cause:** The first prompt told Gemini to use only the notes, to avoid made-up content.
**Solution:** Redesigned the recap into two parts:
"The story so far" (what happens in this book, from Gemini's knowledge plus the publisher description)
and "Where you left off" (the reader's emotions and cliffhangers, from their private notes).
The prompt forbids anything from later books, and tells Gemini to say so if it only knows the description.
Gemini returns JSON so the two parts can be shown separately, and incomplete answers are rejected.
The recap now also works before any notes are written.

**Problem:** After the recap redesign, clicking "Write a new recap" showed "Couldn't reach Gemini",
even though the internet connection and the API key worked.
**Cause:** The new two-part recap is longer, and Gemini's thinking model needed more time than the
40-second limit in the code. The code reported every network problem, including a timeout, as "couldn't reach".
**Solution:** Raised the time limit to 90 seconds, made a timeout automatically fall back to the faster
Flash-Lite model, and added log messages in the terminal so the real cause is visible next time.
