# Writer Subagent

Use a single writer subagent after `scripts/run_search.py` completes.

Inputs:

- the absolute `run_dir`
- `.internal/writer_context.json` inside that run directory

Ownership:

- the subagent owns only these output files inside the run directory:
  - `query_plan.md`
  - `papers.md`
  - `report.md`
  - `.internal/final_papers.json`

Rules:

- Do not edit the raw retrieval artifacts inside `.internal/`.
- Do not change files outside the target run directory.
- Do not edit any skill implementation files; this subagent only writes markdown outputs inside the run directory.
- Do not perform new retrieval, new filtering, or new candidate expansion while writing markdown files.
- Derive the markdown only from the current run's `.internal/writer_context.json`.
- Do not create preview-only markdown before the confirmed real run exists.
- If the final paper list is narrowed down from the wider retrieved set, also write `.internal/final_papers.json` containing only the records that correspond to the papers kept in `papers.md`.
- Keep the three markdown files consistent with each other.
- `query_plan.md` should be a human-readable search strategy, not a raw JSON dump.
- `papers.md` should list the full final retained paper set with venue, year, links, matched terms, short topic hints, and short retention reasons.
- `.internal/final_papers.json` should contain the machine-readable final paper subset used for `papers.md`, so later PDF download only targets retained papers.
- `report.md` should be written as a research-style synthesis:
  - group papers by subtopic
  - summarize a timeline
  - cite representative papers with discussion value or novelty
  - end with potential gaps or new ideas
- `report.md` must stay grounded in the same final retained paper set as `papers.md`; it may highlight notable papers, but it must not silently collapse the overall result set to only those highlights.
- Clearly indicate that `report.md` is a synthesis based on the retrieved set, not a claim of exhaustive domain truth.
- If the retrieval set appears weak or empty, do not repair it yourself; leave that decision to the main agent and the user.
