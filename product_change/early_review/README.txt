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
