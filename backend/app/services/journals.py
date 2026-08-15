from __future__ import annotations

import hashlib
from datetime import datetime
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..models import Alert, Journal, JournalItem, Keyword
from .network import validate_public_url
from .notifications import send_alert_notifications


def _fingerprint(title: str, url: str | None, doi: str | None) -> str:
    value = "|".join([title.strip().lower(), (url or "").strip().lower(), (doi or "").strip().lower()])
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _match(text: str, keywords: list[Keyword]) -> list[str]:
    lowered = text.lower()
    positives = [item.keyword for item in keywords if not item.exclude_flag and item.keyword.lower() in lowered]
    excluded = [item.keyword for item in keywords if item.exclude_flag and item.keyword.lower() in lowered]
    if excluded:
        return []
    return positives


def _fetch_items(journal: Journal) -> list[dict]:
    if journal.rss_url:
        feed = feedparser.parse(_fetch_public_text(journal.rss_url))
        return [
            {
                "title": entry.get("title", "").strip(),
                "authors": entry.get("author", ""),
                "abstract": entry.get("summary", ""),
                "url": entry.get("link", ""),
                "doi": entry.get("doi", ""),
                "published_at": None,
            }
            for entry in feed.entries
            if entry.get("title")
        ]
    if not journal.url:
        return []
    soup = BeautifulSoup(_fetch_public_text(journal.url), "html.parser")
    items = []
    for anchor in soup.select("a"):
        title = anchor.get_text(" ", strip=True)
        href = anchor.get("href")
        if title and href and len(title) > 20:
            items.append(
                {
                    "title": title,
                    "url": urljoin(journal.url, href),
                    "authors": "",
                    "abstract": "",
                    "doi": "",
                }
            )
    return items[:100]


def _fetch_public_text(url: str) -> str:
    current = url
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        for _ in range(5):
            _validate_public_url(current)
            response = client.get(current)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("Redirect response has no location")
                current = urljoin(current, location)
                continue
            response.raise_for_status()
            return response.text
    raise ValueError("Too many redirects")


def _validate_public_url(value: str) -> None:
    validate_public_url(value, "Journal URL")


def monitor_journals(db: Session) -> dict:
    created = 0
    matched = 0
    errors: list[str] = []
    for journal in db.query(Journal).filter(Journal.enabled.is_(True)).all():
        try:
            items = _fetch_items(journal)
            keywords = db.query(Keyword).filter(Keyword.journal_id == journal.id).all()
            for item in items:
                fingerprint = _fingerprint(item["title"], item.get("url"), item.get("doi"))
                if db.query(JournalItem).filter(JournalItem.fingerprint == fingerprint).first():
                    continue
                journal_item = JournalItem(
                    journal_id=journal.id,
                    title=item["title"],
                    authors=item.get("authors"),
                    abstract=item.get("abstract"),
                    url=item.get("url"),
                    doi=item.get("doi") or None,
                    published_at=item.get("published_at"),
                    fingerprint=fingerprint,
                )
                db.add(journal_item)
                db.flush()
                created += 1
                matched_keywords = _match(f"{item['title']} {item.get('abstract', '')}", keywords)
                if matched_keywords:
                    alert = Alert(
                        journal_id=journal.id,
                        journal_item_id=journal_item.id,
                        paper_title=item["title"],
                        paper_url=item.get("url"),
                        matched_keywords=", ".join(matched_keywords),
                    )
                    db.add(alert)
                    db.commit()
                    send_alert_notifications(db, alert)
                    matched += 1
            db.commit()
        except Exception as exc:
            db.rollback()
            errors.append(f"{journal.name}: {exc}")
    return {"created": created, "matched": matched, "errors": errors}
