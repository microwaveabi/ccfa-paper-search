from __future__ import annotations

import datetime as dt
import json
import re
import ssl
import sys
import time
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path.home() / ".codex-data" / "ccf-paper-search"
CACHE_ROOT = DATA_ROOT / "cache"
LOG_ROOT = DATA_ROOT / "logs"
CONFIG_ROOT = DATA_ROOT / "config"
SNAPSHOT_ROOT = SKILL_ROOT / "data" / "ccf_snapshots"

DEFAULT_TIMEOUT = 30
USER_AGENT = "ccf-paper-search/0.1"
_ACTIVE_RUN_LOG: Path | None = None
_LOG_LOCK = threading.Lock()


def ensure_runtime_dirs() -> None:
    for path in (DATA_ROOT, CACHE_ROOT, LOG_ROOT, CONFIG_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def configure_run_logging(run_dir: Path) -> Path:
    global _ACTIVE_RUN_LOG
    log_path = run_dir / ".internal" / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _ACTIVE_RUN_LOG = log_path
    return log_path


def clear_run_logging() -> None:
    global _ACTIVE_RUN_LOG
    _ACTIVE_RUN_LOG = None


def log_event(message: str) -> None:
    timestamp = dt.datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {message}"
    with _LOG_LOCK:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        if _ACTIVE_RUN_LOG is not None:
            with _ACTIVE_RUN_LOG.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


def log_timed(message: str, started_at: float) -> None:
    elapsed = time.perf_counter() - started_at
    log_event(f"{message} ({elapsed:.2f}s)")


def ssl_context() -> ssl.SSLContext:
    return ssl._create_unverified_context()


def http_json(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
        return json.load(resp)


def http_bytes(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> tuple[bytes, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
        data = resp.read()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return data, headers


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    normalized = normalize_text(value).replace(" ", "-")
    return normalized[:80] or "query"


def utc_timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def task_dir_for_topic(topic: str, output_root: Path | None = None) -> Path:
    ensure_runtime_dirs()
    base_root = (output_root or Path.cwd()).resolve()
    base_root.mkdir(parents=True, exist_ok=True)
    path = base_root / f"ccf-paper-search-{utc_timestamp()}-{slugify(topic)}"
    path.mkdir(parents=True, exist_ok=True)
    (path / "pdf").mkdir(exist_ok=True)
    return path


def load_snapshot(year: int) -> list[dict[str, Any]]:
    with (SNAPSHOT_ROOT / f"{year}-a.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_dblp_conf_slug(value: str | None) -> str | None:
    if not value:
        return None
    patterns = [
        r"/db/conf/([^/]+)/",
        r"/rec/conf/([^/]+)/",
        r"/conf/([^/]+)/",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1).lower()
    return None


def snapshot_conf_slugs(item: dict[str, Any]) -> set[str]:
    slugs: set[str] = set()
    dblp_slug = extract_dblp_conf_slug(item.get("dblp_url"))
    if dblp_slug:
        slugs.add(dblp_slug)
    return slugs


def conference_match(
    value: str | None,
    snapshots: list[dict[str, Any]],
    *,
    record_url: str | None = None,
) -> dict[str, Any] | None:
    record_slug = extract_dblp_conf_slug(record_url)
    if record_slug:
        for item in snapshots:
            if record_slug in snapshot_conf_slugs(item):
                return item

    candidate = normalize_text(value)
    if not candidate:
        return None
    for item in snapshots:
        aliases = [item.get("abbr"), item.get("full_name"), *(item.get("aliases") or [])]
        for alias in aliases:
            alias_norm = normalize_text(alias)
            if alias_norm and candidate == alias_norm:
                return item
    return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def safe_filename(value: str, suffix: str = ".pdf") -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    if not base:
        base = "paper"
    return f"{base[:120]}{suffix}"


def unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def fetch_error_message(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"http_{exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return str(exc.reason)
    return str(exc)
