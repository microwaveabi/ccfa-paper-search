# Workflow

1. Let Codex resolve the user's natural language into explicit structured arguments.
2. Keep years within `2023-2026`.
3. Convert Chinese topic wording into an English research topic.
4. Before previewing, do one lightweight external search pass to collect recent, high-signal related terms and neighboring concepts for the topic.
5. Generate broad-recall search terms dynamically, combining topic understanding with the external-search findings.
6. Treat ordinary retrieval requests as read-only use of the existing skill implementation.
7. Do not edit scripts or skill files during retrieval just to improve speed or reliability.
8. If the current run is slow, prefer waiting longer instead of patching the code.
9. Only change the implementation if the user explicitly asks to modify the skill or explicitly approves a code change.
10. Before any real search, present a complete Chinese preview directly in the conversation. Do not create a run directory or write preview files to disk yet.
11. The preview must list years, topic interpretation, all terms, a short Chinese explanation for each term, which terms came from external-search strengthening, the save-directory choice, and the files that will be generated after execution.
12. If save-directory preference is unspecified, the preview must say that explicitly and explain that the default is a new run folder under the current terminal working directory.
13. If PDF preference is unspecified, the same preview must say that explicitly, then ask the short PDF follow-up question.
14. Do not run `scripts/run_search.py` until the user explicitly confirms the current previewed plan.
15. If the plan changes after a failed or weak run, go back to preview and confirmation instead of silently rerunning.
16. Expand the first-pass term set as broadly as practical before the real retrieval run; do not rely on a second retrieval pass to discover core topic terms.
17. After confirmation, prefer enumerating DBLP proceedings pages for the requested CCF-A conferences and years, then filter locally by the pre-expanded topic terms.
18. Execute independent retrieval tasks in parallel when safe, especially conference enumeration, per-term DBLP search, and per-term OpenAlex search.
19. Use `scripts/run_search.py`, and pass `--output-root <directory>` when the user explicitly requested a save directory. Otherwise let the script default to the current terminal working directory.
20. During execution, print visible progress logs for major steps so long runs remain observable.
21. Treat the produced retrieval set as frozen for that run; derive markdown outputs only from that set.
22. Spawn one writer subagent to read `.internal/writer_context.json` and write `query_plan.md`, `papers.md`, `report.md`, and `.internal/final_papers.json` only after the real run exists.
23. The writer should keep `papers.md` and `report.md` grounded in the same final retained paper set instead of shrinking the narrative to only a tiny highlighted subset.
24. If PDF download was requested, run a dedicated PDF-download step only after `.internal/final_papers.json` exists, and target only that final retained subset.
25. For health checks, use `scripts/doctor.py`.
26. Report the absolute run directory path after execution and say whether the summary came directly from that confirmed run.
