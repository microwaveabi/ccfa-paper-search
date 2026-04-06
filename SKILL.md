---
name: ccf-paper-search
description: Search and save topic-related papers from CCF-A conferences across 2023, 2024, 2025, and 2026 using a global personal Codex skill. Use when the user asks to find CCF-A conference papers by topic, save results locally, preview a search plan before execution, or check whether the paper-search skill is working.
---

# CCF Paper Search

Use this skill only for `2023-2026` `CCF-A` conference-paper search.

## Purpose

- Search by topic inside the supported `CCF-A` scope.
- Preview the search plan before any real retrieval.
- Save outputs under a user-chosen directory or, by default, a new run folder under the current terminal working directory.
- Use one writer subagent to write the final markdown files.
- Emit visible runtime logs during execution so long runs remain observable.

## Default Mode

- Default mode is read-only use, not skill development.
- During ordinary paper-search sessions, do not edit files under `scripts/`, `references/`, `data/`, or other skill files.
- Do not change execution paths, add flags, patch scripts, or rewrite prompts just to make a run faster or easier.
- If a run is slow, prefer waiting longer.
- Only modify the skill if the user explicitly asks to change the skill or explicitly approves a code change.

## Required Flow

1. Convert the user request into explicit years, topic, and English search terms.
2. Keep the scope inside `2023-2026` and `CCF-A`.
3. Before presenting any preview, do one lightweight external search pass to discover recent high-signal related terms, subtopics, and neighboring concepts for the query.
4. Use that external search pass to strengthen the first-pass term set; do not rely on a second retrieval round to discover core terms.
5. The preview itself should be shown directly in the conversation and should not create a run directory or write `query_plan.md` yet.
6. During preview generation, clearly separate:
   - terms derived from direct topic understanding
   - terms added because external search suggests they are recent, common, or high-signal in the topic area
7. Before any real search, present one complete Chinese preview.
8. The preview must include:
   - year range
   - Chinese topic summary
   - English topic summary
   - all planned search terms with short Chinese explanations in parentheses
   - which terms were strengthened by the external-search pass
   - whether the user wants to specify a save directory, or an explicit note that the default save location will be a new run folder under the current terminal working directory
   - whether PDF download is enabled, or an explicit note that the user still needs to choose
   - a short note that the search will use a single retrieval pass with the pre-expanded term set, and will execute independent retrieval tasks in parallel when safe
   - the final outputs and what each file is for
9. If save-directory preference is unspecified, ask one short explicit follow-up after the full preview.
10. If PDF preference is unspecified, ask one short explicit PDF follow-up after the full preview.
11. Do not run real retrieval until the user explicitly confirms the current previewed plan, including save-directory choice and PDF choice.
12. After confirmation, run `python scripts/run_search.py ...` for the real search.
13. Only after the real run finishes, use one writer subagent to write `query_plan.md`, `papers.md`, `report.md`, and `.internal/final_papers.json` into the confirmed run directory.
14. If PDF download was requested, perform it only after `.internal/final_papers.json` exists, and download PDFs only for that final retained paper set.

## Hard Constraints

- Freeze the retrieval set per run. Markdown outputs for a run must be derived only from that run's confirmed retrieval set.
- If the plan changes in any material way, previous confirmation is invalid.
- Material changes include venue scope, year scope, keyword set, filtering logic, or precision/recall mode.
- If the plan changes after a weak or failed run, go back to preview and confirmation before rerunning.
- The external-search term-discovery pass is mandatory for topic preview generation; do not skip it for convenience.
- Do not perform hidden second-pass retrieval planning while writing markdown outputs.
- Do not download PDFs from the wide candidate set; only download PDFs from the final retained paper subset.
- Manual markdown authoring is allowed, but it must remain traceable to the current run's confirmed retrieval set or `.internal/writer_context.json`.
- Final user-facing summaries must state which `run_dir` they are based on and whether they were derived from that confirmed retrieval set.

## Interaction Rules

- Default behavior is `preview first, search second`.
- Default retrieval behavior is `one expanded pass`, not `first pass plus follow-up retrieval pass`.
- Default preview behavior is `display first, persist later`; do not write preview artifacts to disk before confirmation.
- A confirmation applies only to the currently previewed plan.
- If the user does not specify a save directory, default to a new run folder under the current terminal working directory.
- If a run returns empty or poor results, report that first. Do not silently switch to a new keyword set or filtering plan.
- Treat short affirmative replies to the current preview as confirmation.
- Treat replies that add PDF permission to the current preview as confirmation plus PDF preference.
- Treat replies that change years, scope, keywords, or filtering intent as plan revision requests.
- If the user already specified PDF preference in the first request, reflect it in the preview and do not ask again.

## Output Meaning

- `query_plan.md`: human-readable search strategy
- `papers.md`: the final retained paper set with venue, year, links, matched terms, retention reasons, and optional importance markers
- `report.md`: a research-style synthesis based on the same final retained paper set, including subtopics, trends, notable papers, and potential gaps or ideas
- `pdf/`: downloaded open-access PDFs when enabled
- `.internal/run.log`: step-by-step execution log for long-running searches
- `.internal/writer_context.json`: machine-readable input for the writer subagent
- `.internal/final_papers.json`: machine-readable final retained paper subset used for `papers.md` and PDF download

## Commands

- Health check: `python scripts/doctor.py`
- Real search: `python scripts/run_search.py ...`
- Optional output root: `--output-root <directory>`

## References

- Read `references/workflow.md` for the execution sequence.
- Read `references/query-expansion.md` for dynamic expansion principles.
- Read `references/dedupe-policy.md` for merge rules.
- Read `references/pdf-policy.md` for PDF boundaries.
- Read `references/output-spec.md` for artifact expectations.
- Read `references/writer-subagent.md` before spawning the markdown-writing subagent.
