# Output Spec

Every executed run should write under a dedicated run directory:

- if the user specified a save directory: `<chosen-directory>/ccf-paper-search-YYYYMMDD-HHMMSS-topic-slug/`
- otherwise: `<current-terminal-working-directory>/ccf-paper-search-YYYYMMDD-HHMMSS-topic-slug/`

Expected files:

- `query_plan.md`: human-readable search strategy
- `papers.md`: the final retained paper set with venue, year, links, matched terms, retention reasons, and optional importance markers
- `report.md`: a research-style synthesis based on that same final retained paper set
- `pdf/`: downloaded open-access PDFs when enabled
- `.internal/run.log`: runtime progress log for slow searches
- `.internal/writer_context.json`: machine-readable input for the writer subagent
- `.internal/final_papers.json`: machine-readable final retained paper subset used for `papers.md`

Interaction expectation:

- The user should normally see a preview first.
- The preview should be shown directly in the conversation and should not create a run directory or write preview files to disk yet.
- Actual retrieval should begin only after explicit confirmation.
- Before previewing, do one lightweight external-search pass to discover recent high-signal related terms for the topic.
- The preview should indicate which terms were strengthened by that external-search pass.
- The preview should also ask whether the user wants to specify a save directory.
- If the user does not specify a save directory, the preview should clearly say that the default output location is a new run folder under the current terminal working directory.
- If PDF preference is unspecified, the preview should say that explicitly and ask before the execution run.
- The preview should tell the user these files will be generated and briefly explain each one.
- The preview should describe the retrieval as a single expanded pass, not a hidden follow-up retrieval cycle.
- The Python scripts should not be the final authors of the markdown files; the writer subagent should be.
- `query_plan.md` should be written only after the confirmed real run exists, not during preview.
- Markdown outputs must be derived only from the confirmed retrieval set for that run.
- `papers.md` and `report.md` should both stay grounded in the same final retained paper set rather than collapsing the final answer to only a tiny highlighted subset.
- If PDF download is enabled, defer actual PDF downloading until the final retained paper subset exists, then download only for that subset.
- If a rerun uses a changed plan, preview and confirmation must happen again before those outputs are generated.
- Final summaries should state which run directory they are based on.
