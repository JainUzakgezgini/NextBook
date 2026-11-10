"""Generates the private 'Previously on...' recap with the Gemini API."""
import json

import requests
from flask import current_app

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Tried in order. The '-latest' aliases always point to Google's current Flash models,
# so the app keeps working when an older model name is retired.
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]


class RecapError(Exception):
    pass


def build_prompt(book, notes):
    series = ""
    if book.series_name or book.series_index:
        series = " (book {} of the {} series)".format(book.series_index or "?", book.series_name or "unnamed")
    lines = []
    for note in reversed(notes):  # oldest first, the order the reader wrote them
        tag = "[CLIFFHANGER] " if note.is_cliffhanger else ""
        lines.append(f"- {tag}{note.content.strip()}")
    notes_text = "\n".join(lines) if lines else "(The reader has not written any notes.)"
    description = (book.description or "").strip()[:2000] or "(No description available.)"
    return (
        "You help a reader who finished a book get ready for the next one in the series.\n"
        f"Book: \"{book.title}\" by {book.authors or 'an unknown author'}{series}.\n\n"
        "Write two parts:\n"
        "1. \"story\": a recap of what happens in THIS book: the main characters, the key events "
        "and how it ends. 6 to 10 sentences. The reader has already read it, so plot details from this "
        "book are fine. Use your own knowledge of the book and the publisher description below.\n"
        "2. \"you\": 3 to 5 sentences, addressed to the reader as 'you', in a warm, personal tone. "
        "Weave their private notes together with the story: connect each feeling, cliffhanger and open "
        "question they wrote to the moment in the book it belongs to (e.g. 'When X happened, you were...'). "
        "End with the questions they are taking into the next book. Their feelings and questions must come "
        "ONLY from the notes, never invent reactions. If there are no notes, use an empty string.\n\n"
        "Rules:\n"
        "- Never mention or guess anything that happens in LATER books of the series.\n"
        "- Do not invent events. If you don't know this specific book well, base the story only on the "
        "description and the notes, and start the story with: 'Based on the book description:'.\n"
        "- Plain text inside the JSON values, no markdown.\n"
        "- Write both parts in the language the notes are written in. If there are no notes, write in English.\n"
        "- Reply with JSON only, exactly in this shape: {\"story\": \"...\", \"you\": \"...\"}\n\n"
        f"Publisher description:\n{description}\n\n"
        f"Reader's private notes:\n{notes_text}"
    )


def parse_recap(text):
    """Turn the stored recap into {'story': ..., 'you': ...}. Old plain-text recaps still work."""
    if not text:
        return None
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and (data.get("story") or data.get("you")):
            return {"story": str(data.get("story") or "").strip(), "you": str(data.get("you") or "").strip()}
    except ValueError:
        pass
    return {"story": text.strip(), "you": ""}


def generate_recap(book, notes):
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise RecapError("The Gemini API key is missing. Add GEMINI_API_KEY to the .env file and restart the app.")

    models = [m for m in [current_app.config.get("GEMINI_MODEL")] + FALLBACK_MODELS if m]
    body = {
        "contents": [{"role": "user", "parts": [{"text": build_prompt(book, notes)}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 3000, "responseMimeType": "application/json"},
    }
    last_error = "Gemini didn't answer."
    for model in dict.fromkeys(models):  # removes duplicates, keeps order
        try:
            resp = requests.post(
                API_URL.format(model=model),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=body,
                timeout=90,
            )
        except requests.Timeout:
            # Thinking models can be slow on long answers: try the next (faster) model
            current_app.logger.warning("Gemini model %s timed out", model)
            last_error = "Gemini took too long to answer. Try again in a moment."
            continue
        except requests.RequestException as exc:
            current_app.logger.warning("Gemini request failed: %r", exc)
            raise RecapError("Couldn't reach Gemini. Check your internet connection and try again.")
        current_app.logger.info("Gemini model %s answered with status %s", model, resp.status_code)

        if resp.status_code == 404:  # model name retired or unknown: try the next one
            last_error = f"Model '{model}' isn't available."
            continue
        if resp.status_code == 429:
            raise RecapError("The free Gemini quota is used up for now. Wait a minute (or until tomorrow) and try again.")
        if resp.status_code in (400, 401, 403):
            message = resp.json().get("error", {}).get("message", "") if resp.content else ""
            if "API key" in message or resp.status_code in (401, 403):
                raise RecapError("Gemini rejected the API key. Check GEMINI_API_KEY in the .env file.")
            raise RecapError(f"Gemini couldn't process the request: {message[:200]}")
        if not resp.ok:
            last_error = f"Gemini error {resp.status_code}."
            continue

        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError):
            text = ""
        parsed = parse_recap(text)
        if parsed and parsed["story"] and not parsed["story"].lstrip().startswith("{"):
            return json.dumps(parsed, ensure_ascii=False)
        last_error = "Gemini returned an incomplete answer. Try again."
    raise RecapError(last_error)
