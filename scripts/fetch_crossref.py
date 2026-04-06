from __future__ import annotations

import urllib.parse

from common import http_json


def enrich_record(record: dict) -> dict:
    if record.get("doi") or not record.get("title"):
        return record
    query = urllib.parse.quote(record["title"])
    payload = http_json(f"https://api.crossref.org/works?query.title={query}&rows=1")
    items = payload.get("message", {}).get("items", [])
    if not items:
        return record
    item = items[0]
    doi = item.get("DOI")
    if doi and not record.get("doi"):
        record["doi"] = f"https://doi.org/{doi}" if not str(doi).startswith("http") else doi
    links = item.get("link", [])
    if links and not record.get("landing_url"):
        record["landing_url"] = links[0].get("URL")
    return record
