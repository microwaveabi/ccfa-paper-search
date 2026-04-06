from __future__ import annotations

import sys

from common import DATA_ROOT, SKILL_ROOT, SNAPSHOT_ROOT, ensure_runtime_dirs, http_json, print_json


def main() -> None:
    ensure_runtime_dirs()
    checks: dict[str, object] = {
        "python_version": sys.version.split()[0],
        "skill_root": str(SKILL_ROOT),
        "data_root": str(DATA_ROOT),
        "snapshots": {},
        "network": {},
    }

    for year in (2023, 2024, 2025, 2026):
        checks["snapshots"][str(year)] = (SNAPSHOT_ROOT / f"{year}-a.json").exists()

    try:
        openalex = http_json("https://api.openalex.org/works?search=reinforcement%20learning&per-page=1")
        checks["network"]["openalex"] = bool(openalex.get("results"))
    except Exception as exc:  # noqa: BLE001
        checks["network"]["openalex"] = str(exc)

    try:
        dblp = http_json("https://dblp.org/search/publ/api?q=reinforcement%20learning&h=1&format=json")
        checks["network"]["dblp"] = "hit" in dblp.get("result", {}).get("hits", {})
    except Exception as exc:  # noqa: BLE001
        checks["network"]["dblp"] = str(exc)

    try:
        crossref = http_json("https://api.crossref.org/works?query.title=reinforcement%20learning&rows=1")
        checks["network"]["crossref"] = bool(crossref.get("message", {}).get("items"))
    except Exception as exc:  # noqa: BLE001
        checks["network"]["crossref"] = str(exc)

    checks["ok"] = all(checks["snapshots"].values()) and all(value is True for value in checks["network"].values())
    print_json(checks)


if __name__ == "__main__":
    main()
