from __future__ import annotations

from pathlib import Path

from common import log_event, write_json


def writer_context_path(run_dir: Path) -> Path:
    return run_dir / ".internal" / "writer_context.json"


def write_writer_context(
    run_dir: Path,
    *,
    plan: dict,
    records: list[dict],
    manifest: list[dict],
    source_failures: list[str],
) -> Path:
    log_event(
        f"Writer context write start; run_dir={run_dir} papers={len(records)} manifest={len(manifest)}"
    )
    payload = {
        "plan": plan,
        "papers": records,
        "manifest": manifest,
        "source_failures": source_failures,
        "outputs": {
            "query_plan_md": str(run_dir / "query_plan.md"),
            "papers_md": str(run_dir / "papers.md"),
            "report_md": str(run_dir / "report.md"),
            "pdf_dir": str(run_dir / "pdf"),
        },
    }
    path = writer_context_path(run_dir)
    write_json(path, payload)
    log_event(f"Writer context write done; path={path}")
    return path
