from __future__ import annotations

from common import normalize_text, unique_strings


def _record_key(record: dict) -> tuple[str, str]:
    doi = (record.get("doi") or "").strip().lower()
    if doi:
        return ("doi", doi)
    return ("title", normalize_text(record.get("title", "")))


def merge_records(records: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str], dict] = {}
    for record in records:
        key = _record_key(record)
        current = merged.get(key)
        if current is None:
            current = {
                "title": record.get("title", ""),
                "year": record.get("year"),
                "conference_abbr": record.get("conference_abbr"),
                "conference_name": record.get("conference_name"),
                "field": record.get("field"),
                "authors": list(record.get("authors") or []),
                "doi": record.get("doi"),
                "landing_url": record.get("landing_url"),
                "pdf_url": record.get("pdf_url"),
                "sources": [record.get("source")] if record.get("source") else [],
                "search_terms": [record.get("search_term")] if record.get("search_term") else [],
                "openalex_id": record.get("openalex_id"),
                "dblp_url": record.get("dblp_url"),
            }
            merged[key] = current
            continue
        current["authors"] = unique_strings([*(current.get("authors") or []), *(record.get("authors") or [])])
        current["sources"] = unique_strings([*(current.get("sources") or []), record.get("source", "")])
        current["search_terms"] = unique_strings([*(current.get("search_terms") or []), record.get("search_term", "")])
        if not current.get("doi") and record.get("doi"):
            current["doi"] = record["doi"]
        if not current.get("landing_url") and record.get("landing_url"):
            current["landing_url"] = record["landing_url"]
        if not current.get("pdf_url") and record.get("pdf_url"):
            current["pdf_url"] = record["pdf_url"]
        if not current.get("openalex_id") and record.get("openalex_id"):
            current["openalex_id"] = record["openalex_id"]
        if not current.get("dblp_url") and record.get("dblp_url"):
            current["dblp_url"] = record["dblp_url"]
    return sorted(merged.values(), key=lambda item: (item.get("year") or 0, item.get("conference_abbr") or "", item.get("title") or ""))
