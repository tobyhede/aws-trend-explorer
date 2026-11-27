Product-change review: 2010–2020

This directory holds the evidence for labelling the 2010–2020 records (ADR 0005). It is append-only evidence, not generated output.

Samples, drawn 27 November 2026 before any reading
- sample_protocol.json: seed, method, sizes, the hidden sample's count per year, and SHA-256 hashes of the sources and of both samples.
- hidden_sample.json: 300 of the 8,421 records from early_snapshot, at least 20 from each year and the rest in proportion to each year's records. A different model reads it blind as the audit reference. The labelling readers are not told which records it holds.
- bridge_sample.json: 200 records from the 2025–2026 pass (source_review) and 200 from the 2021–2024 pass (historical_review), with reader inputs only: index, pass, date, URL, title and text. It carries no recorded level, reason or basis, and it never changes a recorded label.

Both samples rank records by SHA-256 of the seed plus the source URL, as the historical audit does.

Commands, from the repository root
- Check, offline: .venv/bin/python product_change/early_samples.py check
- Do not run early_samples.py draw again. Like historical_audit.py prepare and freeze, it is an authoring step that ran once; it refuses to run while sample_protocol.json exists, and drawing with a new seed would destroy the audit's independence. Only the check is part of reproduction.

Labelling (early_label.py)
Labelling is a step of its own, outside the rebuild. The build never calls a model; it replays final.json.

By default the script runs each request as a headless Claude Code session (claude -p) on the maintainer's Claude subscription, with no API key. Each session is fresh and runs from an empty folder, with the reader's system prompt in place of Claude Code's own, no tools, no MCP servers, and no settings, CLAUDE.md files or memory. Claude Code attaches a short account note to the context; nothing else reaches the model. The model that answered is read from the session's usage report and saved with each attempt. With --client api, the script calls the Claude API directly instead; that needs an API key and the separate dependency: .venv/bin/python -m pip install -r product_change/labelling-requirements.txt.

- Reader inputs are index, date, URL, title and text. Ratings are a level, a one-line reason and a confidence, as in the earlier passes.
- The prompt is the Magnitude categories section of DATA_GUIDE.md, verbatim, plus one instruction to rate only the change the text describes at the time it was published, plus the reply format. It is saved in labels/<year>/prompts.json.
- About 25 records per request, each request a fresh context. Two readers on claude-fable-5-2 rate every record and never see each other's ratings. Each disagreement goes to a third reading on the same model, which sees the text and both readers' level, reason and confidence. All three readings are kept.
- A reply missing a record, holding a level outside 1–5, U and NA, giving a reason that is not one line, copying a run of eight words from the announcement text into a reason, or served by another model is rejected and asked again, up to three times. No fallback model is used, so every saved reading comes from the named model.
- Every attempt, with its reply, served model, request or session ID and token use, is saved in labels/<year>/reader_a/, reader_b/ and adjudication/. A chunk with no valid reply after three attempts is saved as chunkNNN.failed.json and stops the run.
- A rerun skips saved chunks. inputs.json and prompts.json are frozen on the first run; a later run with different inputs or prompt stops.
- labels/<year>/final.json holds each record's final level, reason, confidence and basis, with all readings.

Commands, from the repository root
- Label a year: .venv/bin/python product_change/early_label.py label --year 2010
- Check a labelled year, offline: .venv/bin/python product_change/early_label.py check --year 2010
- Checks with canned replies, no network or API key: .venv/bin/python product_change/early_checks.py
