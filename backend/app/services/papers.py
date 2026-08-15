from __future__ import annotations

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import CitationLink, Job, Paper, PaperFile, PaperReference, now
from .files import absolute_storage_path, guess_mime, relative_storage_path, sha256_path
from .llm import get_provider


def _repair_mojibake(text: str) -> str:
    """Recover common GBK bytes exposed as Latin-1 by legacy PDF font maps."""
    if not text or not any("\x80" <= character <= "\xff" for character in text):
        return text
    try:
        candidate = text.encode("latin1").decode("gb18030")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    source_cjk = sum("\u3400" <= character <= "\u9fff" for character in text)
    candidate_cjk = sum("\u3400" <= character <= "\u9fff" for character in candidate)
    if candidate_cjk >= 5 and candidate_cjk > source_cjk * 2:
        return candidate
    return text


def _extract_docx_text(path: Path) -> str:
    from docx import Document

    document = Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def _convert_docx(path: Path) -> Path | None:
    output_dir = settings.storage_path / "converted"
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(path)],
            capture_output=True,
            check=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    candidate = output_dir / f"{path.stem}.pdf"
    return candidate if candidate.exists() else None


def extract_text(path: Path) -> tuple[str, dict]:
    if path.suffix.lower() == ".docx":
        converted = _convert_docx(path)
        if converted:
            path = converted
        else:
            return _extract_docx_text(path), {"pages": 1, "source": "python-docx", "scanned": False}
    try:
        import fitz

        document = fitz.open(path)
        pages = []
        for page in document:
            pages.append(page.get_text("text"))
        text = _repair_mojibake("\n\n".join(pages))
        scanned = len(text.strip()) < max(40, len(pages) * 20)
        if scanned and settings.ocr_enabled:
            text = _try_ocr(path, pages)
        metadata = {"pages": len(pages), "source": "pymupdf", "scanned": scanned}
        if settings.grobid_enabled:
            grobid = _try_grobid(path)
            if grobid:
                metadata["grobid"] = grobid
        return text, metadata
    except ImportError:
        return path.read_text(encoding="utf-8", errors="ignore"), {"pages": 1, "source": "plain-text", "scanned": False}


def _try_ocr(path: Path, existing_pages: list[str]) -> str:
    try:
        from paddleocr import PaddleOCR
        import fitz

        ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        document = fitz.open(path)
        output: list[str] = []
        for index, page in enumerate(document):
            if existing_pages[index].strip():
                output.append(existing_pages[index])
                continue
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_path = settings.storage_path / "parsed" / f"ocr-{path.stem}-{index}.png"
            pixmap.save(image_path)
            result = ocr.ocr(str(image_path), cls=True)
            output.append("\n".join(item[1][0] for line in result if line for item in line))
        return "\n\n".join(output)
    except Exception:
        return "\n\n".join(existing_pages)


def _try_grobid(path: Path) -> dict | None:
    try:
        endpoint = f"{settings.grobid_url.rstrip('/')}/api/processFulltextDocument"
        response = httpx.post(
            endpoint,
            files={"input": (path.name, path.read_bytes(), "application/pdf")},
            timeout=120,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
        namespace = {"tei": "http://www.tei-c.org/ns/1.0"}

        def text_at(selector: str) -> str:
            node = root.find(selector, namespace)
            return " ".join("".join(node.itertext()).split()) if node is not None else ""

        references = []
        for node in root.findall(".//tei:listBibl/tei:biblStruct", namespace):
            value = " ".join("".join(node.itertext()).split())
            if value:
                references.append(value)
        return {
            "title": text_at(".//tei:titleStmt/tei:title"),
            "abstract": text_at(".//tei:profileDesc/tei:abstract"),
            "references": references[:500],
        }
    except (OSError, ET.ParseError, httpx.HTTPError):
        return None


def _parse_references(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    start = None
    for index, line in enumerate(lines):
        if line.lower() in {"references", "bibliography"} or line in {"参考文献", "引用文献"}:
            start = index + 1
            break
    if start is None:
        return []
    references: list[str] = []
    current = ""
    for line in lines[start:]:
        if re.match(r"^\s*(\[[0-9]+\]|[0-9]+[\.)])\s+", line):
            if current:
                references.append(current.strip())
            current = re.sub(r"^\s*(\[[0-9]+\]|[0-9]+[\.)])\s+", "", line)
        elif current:
            current += " " + line
    if current:
        references.append(current.strip())
    return references[:500]


def _parse_citations(text: str) -> list[tuple[int, str]]:
    body = text
    for heading in ("\nReferences", "\nBibliography", "\n参考文献", "\n引用文献"):
        if heading in body:
            body = body.split(heading, 1)[0]
            break
    matches: list[tuple[int, str]] = []
    for match in re.finditer(r"\[([0-9]+)\]", body):
        start = max(0, match.start() - 100)
        end = min(len(body), match.end() + 100)
        matches.append((int(match.group(1)), body[start:end].replace("\n", " ")))
    return matches


def _extract_doi(value: str) -> str | None:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", value, re.IGNORECASE)
    if not match:
        return None
    return match.group(0).rstrip(".,;:)]}")


def _format_citation(metadata: dict) -> str:
    authors = metadata.get("authors") or "未知作者"
    year = metadata.get("year") or "n.d."
    title = metadata.get("title") or "Untitled"
    doi = metadata.get("doi") or ""
    suffix = f" DOI:{doi}" if doi else ""
    return f"{authors}. {title}. {year}.{suffix}".strip()


def _normalize_title(value: str | None) -> str:
    return re.sub(r"[\W_]+", "", (value or "").lower())


def _find_duplicate(db: Session, paper: Paper, extracted: dict) -> Paper | None:
    doi = (extracted.get("doi") or "").strip().lower()
    if doi:
        candidate = (
            db.query(Paper)
            .filter(Paper.id != paper.id, Paper.doi.is_not(None))
            .all()
        )
        for item in candidate:
            if (item.doi or "").strip().lower() == doi:
                return item
    title = _normalize_title(extracted.get("title") or paper.title)
    if len(title) < 8:
        return None
    for item in db.query(Paper).filter(Paper.id != paper.id).all():
        if _normalize_title(item.title) == title:
            return item
    return None


def _merge_duplicate_paper(db: Session, source: Paper, target: Paper, job: Job) -> Paper:
    for item in db.query(PaperReference).filter(PaperReference.paper_id == target.id).all():
        db.delete(item)
    for item in db.query(CitationLink).filter(CitationLink.paper_id == target.id).all():
        db.delete(item)
    db.flush()
    for item in db.query(PaperReference).filter(PaperReference.paper_id == source.id).all():
        item.paper_id = target.id
    for item in db.query(CitationLink).filter(CitationLink.paper_id == source.id).all():
        item.paper_id = target.id
    for item in db.query(PaperFile).filter(PaperFile.paper_id == source.id).all():
        item.paper_id = target.id
    if not target.file_path:
        target.file_path = source.file_path
    target.updated_at = now()
    job.entity_id = target.id
    db.delete(source)
    db.flush()
    return target


def _match_reference(db: Session, raw_text: str, doi: str | None) -> int | None:
    normalized_doi = (doi or "").strip().lower()
    if normalized_doi:
        for paper in db.query(Paper).filter(Paper.doi.is_not(None)).all():
            if (paper.doi or "").strip().lower() == normalized_doi:
                return paper.id
    raw_title = _normalize_title(raw_text)
    if len(raw_title) < 12:
        return None
    for paper in db.query(Paper).filter(Paper.status == "processed").all():
        title = _normalize_title(paper.title)
        if title and (title in raw_title or raw_title in title):
            return paper.id
    return None


def _link_numeric_citations(text: str) -> str:
    return re.sub(r"\[([0-9]+)\]", r"[[\1]](#ref-\1)", text)


def _write_outputs(paper: Paper, text: str, references: list[str]) -> tuple[Path, Path, Path]:
    parsed_dir = settings.storage_path / "parsed"
    txt_path = parsed_dir / f"paper-{paper.id}.txt"
    md_path = parsed_dir / f"paper-{paper.id}.md"
    json_path = parsed_dir / f"paper-{paper.id}.json"
    txt_path.write_text(text, encoding="utf-8")
    md_lines = [f"# {paper.title}", "", _link_numeric_citations(text.strip()), "", "## References", ""]
    md_lines.extend(
        f'<a id="ref-{index}"></a>- [{index}] {reference}' for index, reference in enumerate(references, 1)
    )
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    json_path.write_text(json.dumps({"references": references}, ensure_ascii=False, indent=2), encoding="utf-8")
    return txt_path, md_path, json_path


def process_paper(db: Session, job_id: int) -> None:
    job = db.get(Job, job_id)
    if not job or job.status == "cancelled":
        return
    job.status = "running"
    job.started_at = now()
    job.progress = 5
    db.commit()
    try:
        paper = db.get(Paper, job.entity_id)
        if not paper or not paper.file_path:
            raise ValueError("Paper source file is missing")
        source_path = absolute_storage_path(paper.file_path)
        text, metadata = extract_text(source_path)
        job.progress = 30
        job.message = "Text extracted"
        db.commit()
        grobid_metadata = metadata.get("grobid") or {}
        references = grobid_metadata.get("references") or _parse_references(text)
        citations = _parse_citations(text)
        provider = get_provider()
        extracted = provider.extract_metadata(text, source_path.name)
        duplicate = _find_duplicate(db, paper, extracted)
        if duplicate:
            paper = _merge_duplicate_paper(db, paper, duplicate, job)
        for item in db.query(PaperReference).filter(PaperReference.paper_id == paper.id).all():
            db.delete(item)
        for item in db.query(CitationLink).filter(CitationLink.paper_id == paper.id).all():
            db.delete(item)
        db.flush()
        reference_rows = []
        for index, raw_text in enumerate(references, 1):
            reference = PaperReference(
                paper_id=paper.id,
                raw_text=raw_text,
                citation_order=index,
            doi=_extract_doi(raw_text),
            )
            reference.matched_paper_id = _match_reference(db, raw_text, reference.doi)
            db.add(reference)
            reference_rows.append(reference)
        db.flush()
        for order, context in citations:
            if 1 <= order <= len(reference_rows):
                db.add(
                    CitationLink(
                        paper_id=paper.id,
                        in_text_marker=f"[{order}]",
                        reference_id=reference_rows[order - 1].id,
                        context=context,
                    )
                )
        paper.title = extracted.get("title") or paper.title
        paper.authors = paper.authors or extracted.get("authors")
        paper.year = paper.year or extracted.get("year")
        paper.doi = paper.doi or extracted.get("doi") or None
        paper.abstract = paper.abstract or extracted.get("abstract")
        paper.core_topics = paper.core_topics or extracted.get("core_topics")
        paper.secondary_topics = paper.secondary_topics or extracted.get("secondary_topics")
        paper.innovation_points = paper.innovation_points or extracted.get("innovation_points")
        paper.citation_gbt = _format_citation(extracted)
        paper.extra_metadata = {
            "parser": metadata,
            "llm_provider": provider.name,
            "reference_count": len(references),
            "duplicate_merged": bool(duplicate),
        }
        for old_file in (
            db.query(PaperFile)
            .filter(PaperFile.paper_id == paper.id, PaperFile.kind.in_(["txt", "markdown", "citations"]))
            .all()
        ):
            db.delete(old_file)
        db.flush()
        txt_path, md_path, json_path = _write_outputs(paper, text, references)
        for kind, path in (("txt", txt_path), ("markdown", md_path), ("citations", json_path)):
            db.add(
                PaperFile(
                    paper_id=paper.id,
                    kind=kind,
                    path=relative_storage_path(path),
                    sha256=sha256_path(path),
                    size_bytes=path.stat().st_size,
                    original_name=path.name,
                    extension=path.suffix.lower(),
                    mime_type=guess_mime(path),
                )
            )
        paper.status = "processed"
        paper.updated_at = now()
        job.progress = 100
        job.status = "succeeded"
        job.message = "Paper processed"
        job.result = {"paper_id": paper.id, "references": len(references), "duplicate": bool(duplicate)}
        job.finished_at = now()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = now()
            db.commit()
