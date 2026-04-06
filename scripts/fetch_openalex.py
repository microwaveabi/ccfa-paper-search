from __future__ import annotations

import concurrent.futures
import time
import urllib.parse

from common import conference_match, http_json, log_event, log_timed


def _source_display_name(item: dict) -> str:
    primary = (item.get("primary_location") or {}).get("source") or {}
    if primary.get("display_name"):
        return primary["display_name"]
    best = (item.get("best_oa_location") or {}).get("source") or {}
    return best.get("display_name", "")


def search_openalex(term: str, year: int, snapshots: list[dict], per_page: int = 50, max_pages: int = 3) -> list[dict]:
    started_at = time.perf_counter()
    log_event(f"OpenAlex search start; year={year} term={term!r} per_page={per_page} max_pages={max_pages}")
    results: list[dict] = []
    query = urllib.parse.quote(term)

    def _fetch_page(page: int) -> list[dict]:
        page_started_at = time.perf_counter()
        url = (
            "https://api.openalex.org/works"
            f"?search={query}"
            f"&filter=from_publication_date:{year}-01-01,to_publication_date:{year}-12-31"
            f"&page={page}&per-page={per_page}"
        )
        payload = http_json(url)
        batch = payload.get("results", [])
        log_timed(f"OpenAlex page fetched; year={year} term={term!r} page={page} batch={len(batch)}", page_started_at)
        page_results: list[dict] = []
        for item in batch:
            if item.get("type") != "proceedings-article":
                continue
            matched = conference_match(_source_display_name(item), snapshots)
            if not matched:
                continue
            best_oa = item.get("best_oa_location") or {}
            open_access = item.get("open_access") or {}
            page_results.append(
                {
                    "title": item.get("display_name") or item.get("title") or "",
                    "year": item.get("publication_year", year),
                    "conference_abbr": matched["abbr"],
                    "conference_name": matched["full_name"],
                    "field": matched["field"],
                    "authors": [(a.get("author") or {}).get("display_name", "") for a in item.get("authorships", [])],
                    "doi": item.get("doi"),
                    "landing_url": best_oa.get("landing_page_url"),
                    "pdf_url": best_oa.get("pdf_url") or open_access.get("oa_url"),
                    "openalex_id": item.get("id"),
                    "source": "openalex",
                    "search_term": term,
                }
            )
        return page_results

    worker_count = min(max_pages, 4)
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(_fetch_page, page): page for page in range(1, max_pages + 1)}
        for future in concurrent.futures.as_completed(futures):
            results.extend(future.result())
    log_timed(f"OpenAlex search done; year={year} term={term!r} kept={len(results)}", started_at)
    return results
