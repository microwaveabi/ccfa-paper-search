# Query Expansion

Generate English search terms dynamically per request.

Principles:

- Before freezing a preview, do one lightweight external-search pass to discover recent high-signal terms, hot subtopics, and neighboring concept words for the query.
- Preserve the core topic semantics.
- Prefer high recall over early neatness.
- Generate multiple plausible paper-title phrasings, not just one canonical wording.
- Add abbreviations when they are common and useful.
- Add nearby subtopics, mechanisms, benchmark framings, and alternative task names when they may recover missed papers.
- Include broader but still defensible variants if they can be cleaned up later by venue filtering and deduplication.
- Reject only obviously overbroad or off-topic expansions.
- Keep the final plan auditable and save it into `query_plan.md` and `.internal/writer_context.json`.
- Prefer pushing likely useful concept terms into the first retrieval pass instead of relying on a second retrieval round.
- Do not directly trust noisy auto-generated metadata keywords or topics as the main expansion source.

Useful expansion buckets:

- core phrase
- alternate phrasing
- task framing
- model framing
- memory/context/history framing
- retrieval/planning/reasoning framing
- benchmark/evaluation framing

For hard topics, prefer a larger term set first, then narrow through filtering after retrieval.
