from __future__ import annotations

import concurrent.futures
from pathlib import Path

from common import fetch_error_message, http_bytes, log_event, safe_filename


def derive_pdf_url(record: dict) -> str | None:
    if record.get("pdf_url"):
        return record["pdf_url"]
    landing_url = record.get("landing_url") or ""
    if "aclanthology.org" in landing_url and not landing_url.endswith(".pdf"):
        return landing_url.rstrip("/") + ".pdf"
    return None


def download_open_access_pdfs(records: list[dict], pdf_dir: Path) -> list[dict]:
    pdf_dir.mkdir(parents=True, exist_ok=True)

    def _download_one(index: int, record: dict) -> dict:
        log_event(f"PDF candidate start; item={index}/{len(records)} title={record.get('title', '')!r}")
        url = derive_pdf_url(record)
        status = {
            "title": record.get("title"),
            "conference_abbr": record.get("conference_abbr"),
            "status": "skipped",
            "pdf_path": None,
            "url": url,
        }
        if not url:
            status["status"] = "no_open_access_url"
            log_event(f"PDF candidate skipped; item={index}/{len(records)} reason=no_open_access_url")
            return status
        try:
            data, headers = http_bytes(url, timeout=45)
            content_type = headers.get("content-type", "").lower()
            if not data.startswith(b"%PDF") and "pdf" not in content_type:
                status["status"] = "invalid_pdf"
                log_event(f"PDF candidate invalid; item={index}/{len(records)}")
                return status
            filename = safe_filename(f"{index:04d}_{record.get('conference_abbr', 'conf')}_{record.get('title', '')}")
            target = pdf_dir / filename
            target.write_bytes(data)
            status["status"] = "downloaded"
            status["pdf_path"] = str(target)
            log_event(f"PDF candidate downloaded; item={index}/{len(records)} path={target}")
        except Exception as exc:  # noqa: BLE001
            status["status"] = fetch_error_message(exc)
            log_event(f"PDF candidate failed; item={index}/{len(records)} reason={status['status']}")
        return status

    worker_count = max(1, min(6, len(records)))
    manifest: list[dict | None] = [None] * len(records)
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(_download_one, index, record): index - 1
            for index, record in enumerate(records, start=1)
        }
        for future in concurrent.futures.as_completed(future_map):
            manifest[future_map[future]] = future.result()
    return [item for item in manifest if item is not None]
