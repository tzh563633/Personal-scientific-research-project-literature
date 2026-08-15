from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import httpx

from ..config import settings
from .network import validate_public_url

USER_AGENT = "research-data-platform/1.0"


def _normalize_title(value: str | None) -> str:
    return re.sub(r"[\W_]+", "", (value or "").lower())


def _normalize_doi(value: str | None) -> str:
    return (value or "").lower().strip().removeprefix("https://doi.org/")


def _authors_from_openalex(item: dict) -> str:
    return ", ".join(
        author.get("author", {}).get("display_name", "")
        for author in item.get("authorships", [])
        if author.get("author")
    )


def search_openalex(query: str, limit: int = 10) -> list[dict]:
    response = httpx.get(
        "https://api.openalex.org/works",
        params={"search": query, "per-page": limit},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    results = []
    for item in response.json().get("results", []):
        primary = item.get("primary_location") or {}
        best_location = item.get("best_oa_location") or {}
        results.append(
            {
                "title": item.get("title") or "",
                "authors": _authors_from_openalex(item),
                "year": item.get("publication_year"),
                "doi": _normalize_doi(item.get("doi")),
                "url": primary.get("landing_page_url") or item.get("id"),
                "pdf_url": best_location.get("pdf_url"),
                "abstract": "",
                "citation": "",
                "source": "openalex",
            }
        )
    return results


def search_crossref(query: str, limit: int = 10) -> list[dict]:
    response = httpx.get(
        "https://api.crossref.org/works",
        params={"query.bibliographic": query, "rows": limit},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    results = []
    for item in response.json().get("message", {}).get("items", []):
        authors = ", ".join(
            f"{author.get('given', '')} {author.get('family', '')}".strip()
            for author in item.get("author", [])
        )
        pdf_url = next(
            (
                link.get("URL")
                for link in item.get("link", [])
                if "pdf" in (link.get("content-type") or "").lower()
            ),
            None,
        )
        results.append(
            {
                "title": (item.get("title") or [""])[0],
                "authors": authors,
                "year": (item.get("published-print") or item.get("published-online") or {}).get(
                    "date-parts", [[None]]
                )[0][0],
                "doi": _normalize_doi(item.get("DOI")),
                "url": item.get("URL"),
                "pdf_url": pdf_url,
                "abstract": item.get("abstract", ""),
                "citation": "",
                "source": "crossref",
            }
        )
    return results


def search_semantic_scholar(query: str, limit: int = 10) -> list[dict]:
    response = httpx.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,abstract,externalIds,url,openAccessPdf",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    results = []
    for item in response.json().get("data", []):
        external_ids = item.get("externalIds") or {}
        open_access = item.get("openAccessPdf") or {}
        results.append(
            {
                "title": item.get("title") or "",
                "authors": ", ".join(author.get("name", "") for author in item.get("authors", [])),
                "year": item.get("year"),
                "doi": _normalize_doi(external_ids.get("DOI")),
                "url": item.get("url"),
                "pdf_url": open_access.get("url"),
                "abstract": item.get("abstract") or "",
                "citation": "",
                "source": "semantic_scholar",
            }
        )
    return results


def search_academic_sources(query: str, limit: int = 5) -> list[dict]:
    results: list[dict] = []
    for searcher in (search_openalex, search_crossref, search_semantic_scholar):
        try:
            results.extend(searcher(query, limit=limit))
        except Exception:
            continue
    unique: dict[str, dict] = {}
    for result in results:
        key = _normalize_doi(result.get("doi")) or _normalize_title(result.get("title"))
        if key and key not in unique:
            unique[key] = result
    return list(unique.values())


def _validate_public_url(value: str) -> None:
    validate_public_url(value, "External source URL")


def _download_binary(url: str) -> tuple[bytes, str]:
    current = url
    with httpx.Client(timeout=60, follow_redirects=False) as client:
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
            return response.content, response.headers.get("content-type", "")
    raise ValueError("Too many redirects")


def download_source_pdf(source: dict, destination_dir: Path) -> Path | None:
    candidates = [source.get("pdf_url")]
    if not candidates[0] and source.get("url", "").lower().endswith(".pdf"):
        candidates.append(source.get("url"))
    for url in candidates:
        if not url:
            continue
        try:
            payload, content_type = _download_binary(url)
            if not payload.startswith(b"%PDF-") and "pdf" not in content_type.lower():
                continue
            digest = hashlib.sha256(payload).hexdigest()
            destination_dir.mkdir(parents=True, exist_ok=True)
            path = destination_dir / f"external-{digest}.pdf"
            path.write_bytes(payload)
            return path
        except (OSError, ValueError, httpx.HTTPError):
            continue
    return None


def verify_external_source(source: dict) -> bool:
    doi = _normalize_doi(source.get("doi"))
    title = _normalize_title(source.get("title"))
    if not doi and not title:
        return False
    try:
        if doi:
            response = httpx.get(
                f"https://api.crossref.org/works/{quote(doi, safe='')}",
                headers={"User-Agent": USER_AGENT},
                timeout=20,
            )
            response.raise_for_status()
            item = response.json().get("message", {})
            return _normalize_doi(item.get("DOI")) == doi
        results = search_crossref(source.get("title", ""), limit=3)
        return any(_normalize_title(item.get("title")) == title for item in results)
    except Exception:
        return False


def fact_check(source: dict, local_papers: list) -> bool:
    doi = _normalize_doi(source.get("doi"))
    title = _normalize_title(source.get("title"))
    for paper in local_papers:
        if doi and _normalize_doi(paper.doi) == doi:
            return True
        if title and _normalize_title(paper.title) == title:
            return True
    return bool(source.get("verified") and source.get("verified_by"))
