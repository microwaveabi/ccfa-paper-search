from __future__ import annotations

import concurrent.futures
import html
import json
import time
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

from common import CACHE_ROOT, conference_match, http_bytes, http_json, log_event, log_timed, normalize_text, unique_strings, write_json


STOP_TOKENS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "toward",
    "towards",
    "under",
    "using",
    "via",
    "with",
}


class DblpIndexParser(HTMLParser):
    def __init__(self, year: int) -> None:
        super().__init__()
        self.year = str(year)
        self.toc_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        href = attr_map.get("href") or ""
        if "/db/conf/" not in href or not href.endswith(".html"):
            return
        if "/index.html" in href or f"{self.year}" not in href:
            return
        if "/rec/" in href:
            return
        self.toc_urls.append(href)


class DblpTocParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[dict] = []
        self.current: dict | None = None
        self.current_title: list[str] = []
        self.current_author: list[str] = []
        self.in_title = False
        self.in_author_name = False
        self.entry_li_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        class_attr = attr_map.get("class") or ""
        if tag == "li" and "entry" in class_attr and "inproceedings" in class_attr:
            self.current = {"authors": []}
            self.current_title = []
            self.entry_li_depth = 1
            return
        if self.current is None:
            return
        if tag == "li":
            self.entry_li_depth += 1
            return
        if tag == "span" and attr_map.get("class") == "title":
            self.in_title = True
            self.current_title = []
            return
        if tag == "span" and attr_map.get("itemprop") == "name":
            self.in_author_name = True
            self.current_author = []
            return
        if tag == "a":
            href = attr_map.get("href") or ""
            if "/rec/" in href and href.endswith(".html") and not self.current.get("dblp_url"):
                self.current["dblp_url"] = href
            if href and not self.current.get("landing_url") and "/rec/" not in href and "?view=" not in href:
                self.current["landing_url"] = href

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        if self.in_title:
            self.current_title.append(data)
        if self.in_author_name:
            self.current_author.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag == "span" and self.in_title:
            title = html.unescape("".join(self.current_title)).strip()
            if title:
                self.current["title"] = title
            self.in_title = False
            self.current_title = []
            return
        if tag == "span" and self.in_author_name:
            author = html.unescape("".join(self.current_author)).strip()
            if author:
                self.current.setdefault("authors", []).append(author)
            self.in_author_name = False
            self.current_author = []
            return
        if tag == "li" and self.current is not None:
            self.entry_li_depth -= 1
            if self.entry_li_depth <= 0:
                title = (self.current.get("title") or "").strip()
                if title:
                    self.entries.append(self.current)
                self.current = None
                self.current_title = []
                self.current_author = []
                self.in_title = False
                self.in_author_name = False
                self.entry_li_depth = 0


def _normalized_term_tokens(term: str) -> list[str]:
    return [token for token in normalize_text(term).split() if token and token not in STOP_TOKENS]


def title_matches_terms(title: str, include_terms: list[str], exclude_terms: list[str] | None = None) -> list[str]:
    normalized_title = normalize_text(title)
    if not normalized_title:
        return []
    for term in exclude_terms or []:
        term_norm = normalize_text(term)
        if term_norm and term_norm in normalized_title:
            return []

    matched: list[str] = []
    for term in include_terms:
        term_norm = normalize_text(term)
        if not term_norm:
            continue
        if term_norm in normalized_title:
            matched.append(term)
            continue
        tokens = _normalized_term_tokens(term)
        if len(tokens) >= 2 and all(token in normalized_title.split() for token in tokens):
            matched.append(term)
    return unique_strings(matched)


def _fetch_dblp_html(url: str) -> str:
    data, _headers = http_bytes(url, timeout=60)
    return data.decode("utf-8", errors="ignore")


def proceedings_cache_path(snapshot: dict, year: int) -> Path:
    cache_dir = CACHE_ROOT / "dblp-toc"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{year}-{snapshot['abbr']}.json"


def proceedings_toc_urls(snapshot: dict, year: int) -> list[str]:
    index_url = snapshot.get("dblp_url") or ""
    if not index_url:
        log_event(f"DBLP index skipped for {snapshot.get('abbr')} {year}: no dblp_url")
        return []
    if not index_url.endswith("index.html"):
        index_url = index_url.rstrip("/") + "/index.html"
    started_at = time.perf_counter()
    log_event(f"DBLP index fetch start for {snapshot.get('abbr')} {year}")
    parser = DblpIndexParser(year)
    parser.feed(_fetch_dblp_html(index_url))
    log_timed(f"DBLP index fetch done for {snapshot.get('abbr')} {year}; toc_pages={len(parser.toc_urls)}", started_at)
    return unique_strings(parser.toc_urls)


def enumerate_dblp_proceedings(snapshot: dict, year: int) -> list[dict]:
    cache_path = proceedings_cache_path(snapshot, year)
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        log_event(f"DBLP TOC cache hit for {snapshot['abbr']} {year}; entries={len(cached)}")
        return cached

    started_at = time.perf_counter()
    log_event(f"DBLP TOC enumeration start for {snapshot['abbr']} {year}")
    results: list[dict] = []
    toc_urls = proceedings_toc_urls(snapshot, year)
    if toc_urls:
        worker_count = min(6, len(toc_urls))

        def _parse_toc_page(toc_url: str) -> list[dict]:
            toc_started_at = time.perf_counter()
            log_event(f"DBLP TOC page fetch start for {snapshot['abbr']} {year}: {toc_url}")
            parser = DblpTocParser()
            parser.feed(_fetch_dblp_html(toc_url))
            log_timed(
                f"DBLP TOC page fetch done for {snapshot['abbr']} {year}; page_entries={len(parser.entries)}",
                toc_started_at,
            )
            page_results: list[dict] = []
            for entry in parser.entries:
                page_results.append(
                    {
                        "title": entry.get("title", ""),
                        "year": year,
                        "conference_abbr": snapshot["abbr"],
                        "conference_name": snapshot["full_name"],
                        "field": snapshot["field"],
                        "authors": list(entry.get("authors") or []),
                        "doi": None,
                        "landing_url": entry.get("landing_url"),
                        "dblp_url": entry.get("dblp_url"),
                        "source": "dblp-toc",
                    }
                )
            return page_results

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(_parse_toc_page, toc_url) for toc_url in toc_urls]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
    write_json(cache_path, results)
    log_timed(f"DBLP TOC enumeration done for {snapshot['abbr']} {year}; entries={len(results)}", started_at)
    return results


def filter_enumerated_records(records: list[dict], include_terms: list[str], exclude_terms: list[str] | None = None) -> list[dict]:
    results: list[dict] = []
    for record in records:
        matched_terms = title_matches_terms(record.get("title", ""), include_terms, exclude_terms)
        if not matched_terms:
            continue
        enriched = dict(record)
        enriched["search_term"] = matched_terms[0]
        enriched["matched_terms"] = matched_terms
        results.append(enriched)
    log_event(
        f"Local TOC filter complete; source_records={len(records)} matched_records={len(results)} terms={len(include_terms)}"
    )
    return results


def search_dblp(term: str, year: int, snapshots: list[dict], limit: int = 200) -> list[dict]:
    started_at = time.perf_counter()
    log_event(f"DBLP search start; year={year} term={term!r} limit={limit}")
    query = urllib.parse.quote(term)
    url = f"https://dblp.org/search/publ/api?q={query}&h={limit}&format=json"
    payload = http_json(url)
    hits = payload.get("result", {}).get("hits", {}).get("hit", [])
    if isinstance(hits, dict):
        hits = [hits]

    results: list[dict] = []
    for hit in hits:
        info = hit.get("info", {})
        if str(info.get("year")) != str(year):
            continue
        if info.get("type") != "Conference and Workshop Papers":
            continue
        matched = conference_match(info.get("venue") or "", snapshots, record_url=info.get("url"))
        if not matched:
            continue
        authors = info.get("authors", {}).get("author", [])
        if isinstance(authors, dict):
            authors = [authors]
        results.append(
            {
                "title": info.get("title", ""),
                "year": year,
                "conference_abbr": matched["abbr"],
                "conference_name": matched["full_name"],
                "field": matched["field"],
                "authors": [a.get("text", "") for a in authors if isinstance(a, dict)],
                "doi": info.get("doi"),
                "landing_url": info.get("ee") if isinstance(info.get("ee"), str) else (info.get("ee") or [None])[0],
                "dblp_url": info.get("url"),
                "source": "dblp",
                "search_term": term,
            }
        )
    log_timed(f"DBLP search done; year={year} term={term!r} raw_hits={len(hits)} kept={len(results)}", started_at)
    return results
