"""Small wrapper around the public Google Books API with a local cache."""
import json
import re
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

from app import db
from app.models import ApiCache

API_URL = "https://www.googleapis.com/books/v1/volumes"
CACHE_HOURS = 24


class BooksAPIError(Exception):
    pass


def _get_json(url, params):
    key = current_app.config.get("GOOGLE_BOOKS_API_KEY")
    if key:
        params = {**params, "key": key}
    try:
        resp = requests.get(url, params=params, timeout=8)
    except requests.RequestException:
        raise BooksAPIError("Couldn't reach Google Books. Check your internet connection and try again.")
    if resp.status_code == 429:
        if not key:
            raise BooksAPIError(
                "Google Books blocks searches without an API key. "
                "Add GOOGLE_BOOKS_API_KEY to the .env file and restart the app."
            )
        raise BooksAPIError("Google Books is getting too many requests right now. Wait a minute and try again.")
    if resp.status_code in (400, 403) and key:
        raise BooksAPIError(
            "Google Books rejected the API key. Check GOOGLE_BOOKS_API_KEY in the .env file "
            "and make sure the Books API is enabled in Google Cloud."
        )
    if resp.status_code == 404:
        return None
    if not resp.ok:
        raise BooksAPIError(f"Google Books answered with an error ({resp.status_code}). Try again in a moment.")
    return resp.json()


def _cached(key, fetch):
    now = datetime.now(timezone.utc)
    hit = db.session.get(ApiCache, key)
    if hit:
        fetched = hit.fetched_at if hit.fetched_at.tzinfo else hit.fetched_at.replace(tzinfo=timezone.utc)
        if now - fetched < timedelta(hours=CACHE_HOURS):
            return json.loads(hit.payload)
    data = fetch()
    if data is not None:
        if hit:
            hit.payload, hit.fetched_at = json.dumps(data), now
        else:
            db.session.add(ApiCache(key=key, payload=json.dumps(data), fetched_at=now))
        db.session.commit()
    return data


def _clean_description(text):
    if not text:
        return None
    text = re.sub(r"<br\s*/?>|</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _parse(item):
    info = item.get("volumeInfo", {})
    images = info.get("imageLinks", {})
    thumb = images.get("thumbnail") or images.get("smallThumbnail")
    if thumb:
        thumb = thumb.replace("http://", "https://").replace("&edge=curl", "")
    series_index = None
    display_number = (info.get("seriesInfo") or {}).get("bookDisplayNumber")
    if display_number and str(display_number).isdigit():
        series_index = int(display_number)
    title = info.get("title", "Untitled")
    return {
        "google_id": item.get("id"),
        "title": title[:300],
        "subtitle": info.get("subtitle"),
        "authors": ", ".join(info.get("authors", []))[:300] or None,
        "thumbnail_url": thumb,
        "description": _clean_description(info.get("description")),
        "published_date": info.get("publishedDate"),
        "page_count": info.get("pageCount"),
        "average_rating": info.get("averageRating"),
        "ratings_count": info.get("ratingsCount"),
        "series_index": series_index,
    }


def normalize(query):
    """'  Fourth   WING ' and 'fourth wing' are the same search."""
    return " ".join((query or "").split()).lower()


def search(query):
    query = normalize(query)
    if not query:
        return []
    data = _cached(
        f"search:{query}",
        lambda: _get_json(API_URL, {"q": query, "maxResults": 20, "printType": "books"}),
    )
    return [_parse(item) for item in (data or {}).get("items", [])]


def get_volume(google_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,40}", google_id or ""):
        return None
    data = _cached(f"volume:{google_id}", lambda: _get_json(f"{API_URL}/{google_id}", {}))
    return _parse(data) if data else None
