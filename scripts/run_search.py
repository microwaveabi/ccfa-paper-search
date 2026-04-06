from __future__ import annotations

import argparse
import concurrent.futures
import time
from pathlib import Path

from common import (
    clear_run_logging,
    configure_run_logging,
    ensure_runtime_dirs,
    load_snapshot,
    log_event,
    log_timed,
    print_json,
    task_dir_for_topic,
    unique_strings,
)
from dedupe import merge_records
from fetch_crossref import enrich_record
from fetch_dblp import enumerate_dblp_proceedings, filter_enumerated_records, search_dblp
from fetch_openalex import search_openalex
from write_outputs import write_writer_context


def build_query_plan(args: argparse.Namespace, final_terms: list[str], seed_terms: list[str]) -> dict:
    return {
        "request": args.request,
        "topic": args.topic,
        "years": args.year,
        "seed_terms": seed_terms,
        "terms": final_terms,
        "exclusions": args.exclude,
        "mode": "broad-recall",
        "download_open_pdfs": args.download_open_pdfs,
    }


def dblp_limit_for_term(term: str) -> int:
    words = [word for word in term.replace("-", " ").split() if word]
    if len(words) <= 3:
        return 600
    if "reinforcement learning" in term.lower():
        return 600
    return 120


ENUMERATION_WORKERS = 6
DBLP_WORKERS = 8
OPENALEX_WORKERS = 4
CROSSREF_WORKERS = 4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--year", action="append", type=int, required=True)
    parser.add_argument("--term", action="append", required=True)
    parser.add_argument("--seed-term", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--output-root")
    parser.add_argument("--skip-enumeration", action="store_true")
    parser.add_argument("--download-open-pdfs", action="store_true")
    args = parser.parse_args()

    ensure_runtime_dirs()
    output_root = Path(args.output_root).expanduser() if args.output_root else None
    run_dir = task_dir_for_topic(args.topic, output_root=output_root)
    configure_run_logging(run_dir)
    started_at = time.perf_counter()
    try:
        log_event(f"Run start; topic={args.topic!r} years={args.year} seed_terms={len(args.term)}")
        final_terms = unique_strings(args.term)
        seed_terms = unique_strings(args.seed_term) or list(final_terms)
        log_event(
            f"Using caller-supplied term set; seed_terms={len(seed_terms)} final_terms={len(final_terms)}"
        )
        plan = build_query_plan(args, final_terms, seed_terms)
        plan["output_root"] = str((output_root or Path.cwd()).resolve())
        plan["run_dir"] = str(run_dir)
        context_path = write_writer_context(
            run_dir,
            plan=plan,
            records=[],
            manifest=[],
            source_failures=[],
        )

        collected: list[dict] = []
        source_failures: list[str] = []
        enumerated_by_year: dict[int, list[dict]] = {}
        snapshots_by_year = {year: load_snapshot(year) for year in args.year}
        for year, snapshots in snapshots_by_year.items():
            log_event(f"Year start; year={year} conferences={len(snapshots)} search_terms={len(final_terms)}")
            enumerated_by_year[year] = []

        enum_jobs = []
        if not args.skip_enumeration:
            for year, snapshots in snapshots_by_year.items():
                for snapshot in snapshots:
                    enum_jobs.append((year, snapshot))
        else:
            for year in args.year:
                log_event(f"DBLP TOC enumeration skipped for year={year}")

        dblp_jobs = [(year, term, snapshots_by_year[year]) for year in args.year for term in final_terms]
        openalex_jobs = [(year, term, snapshots_by_year[year]) for year in args.year for term in final_terms]

        future_meta: dict[concurrent.futures.Future, tuple] = {}
        with (
            concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(ENUMERATION_WORKERS, len(enum_jobs) or 1))) as enum_executor,
            concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(DBLP_WORKERS, len(dblp_jobs) or 1))) as dblp_executor,
            concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(OPENALEX_WORKERS, len(openalex_jobs) or 1))) as openalex_executor,
        ):
            for year, snapshot in enum_jobs:
                future = enum_executor.submit(enumerate_dblp_proceedings, snapshot, year)
                future_meta[future] = ("enum", year, snapshot)

            for year, term, snapshots in dblp_jobs:
                future = dblp_executor.submit(search_dblp, term, year, snapshots, dblp_limit_for_term(term))
                future_meta[future] = ("dblp", year, term)

            for year, term, snapshots in openalex_jobs:
                future = openalex_executor.submit(search_openalex, term, year, snapshots)
                future_meta[future] = ("openalex", year, term)

            for future in concurrent.futures.as_completed(list(future_meta)):
                meta = future_meta[future]
                kind = meta[0]
                if kind == "enum":
                    _kind, year, snapshot = meta
                    try:
                        records = future.result()
                        enumerated_by_year[year].extend(records)
                        collected.extend(filter_enumerated_records(records, final_terms, args.exclude))
                    except Exception as exc:  # noqa: BLE001
                        source_failures.append(f"dblp-toc:{year}:{snapshot.get('abbr')}:{exc}")
                        log_event(f"DBLP TOC enumeration failed; year={year} conf={snapshot.get('abbr')} error={exc}")
                elif kind == "dblp":
                    _kind, year, term = meta
                    try:
                        collected.extend(future.result())
                    except Exception as exc:  # noqa: BLE001
                        source_failures.append(f"dblp:{year}:{term}:{exc}")
                        log_event(f"DBLP search failed; year={year} term={term!r} error={exc}")
                else:
                    _kind, year, term = meta
                    try:
                        collected.extend(future.result())
                    except Exception as exc:  # noqa: BLE001
                        source_failures.append(f"openalex:{year}:{term}:{exc}")
                        log_event(f"OpenAlex search failed; year={year} term={term!r} error={exc}")

        for year in args.year:
            log_event(
                f"Year retrieval done; year={year} enumerated_records={len(enumerated_by_year.get(year, []))}"
            )

        merged = merge_records(collected)
        log_event(f"Merge complete; raw_records={len(collected)} merged_records={len(merged)}")

        crossref_budget = 5
        enrichment_jobs: list[tuple[int, dict]] = []
        enriched = list(merged)
        for index, record in enumerate(merged):
            needs_enrichment = (not record.get("doi")) or (not record.get("landing_url"))
            if needs_enrichment and crossref_budget > 0:
                enrichment_jobs.append((index, record))
                crossref_budget -= 1

        if enrichment_jobs:
            log_event(f"Crossref enrichment batch start; items={len(enrichment_jobs)}")

            def _enrich(index: int, record: dict) -> tuple[int, dict]:
                log_event(
                    f"Crossref enrich start; item={index + 1}/{len(merged)} title={record.get('title', '')!r}"
                )
                enriched_record = enrich_record(dict(record))
                log_event(f"Crossref enrich done; item={index + 1}/{len(merged)}")
                return index, enriched_record

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, min(CROSSREF_WORKERS, len(enrichment_jobs)))
            ) as crossref_executor:
                future_map = {
                    crossref_executor.submit(_enrich, index, record): (index, record)
                    for index, record in enrichment_jobs
                }
                for future in concurrent.futures.as_completed(future_map):
                    index, record = future_map[future]
                    try:
                        enriched_index, enriched_record = future.result()
                        enriched[enriched_index] = enriched_record
                    except Exception as exc:  # noqa: BLE001
                        source_failures.append(f"crossref:{record.get('title', '')}:{exc}")
                        log_event(f"Crossref enrich failed; item={index + 1}/{len(merged)} error={exc}")
        else:
            log_event("Crossref enrichment skipped")

        manifest: list[dict] = []
        if args.download_open_pdfs:
            log_event(
                "PDF download deferred; will download only after the final retained paper set is written"
            )
        else:
            log_event("PDF download skipped")

        context_path = write_writer_context(
            run_dir,
            plan=plan,
            records=enriched,
            manifest=manifest,
            source_failures=source_failures,
        )
        log_timed(f"Run complete; papers={len(enriched)} source_failures={len(source_failures)}", started_at)

        print_json(
            {
                "ok": True,
                "run_dir": str(run_dir),
                "writer_context": str(context_path),
                "paper_count": len(enriched),
                "downloaded_pdf_count": sum(1 for item in manifest if item.get("status") == "downloaded"),
                "source_failures": source_failures,
            }
        )
    finally:
        clear_run_logging()


if __name__ == "__main__":
    main()
