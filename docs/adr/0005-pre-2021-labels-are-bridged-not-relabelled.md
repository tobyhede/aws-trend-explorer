# Pre-2021 labels use a different review protocol, measured with a bridge sample

The corpus is extended back to 2010 to compare substantive output across the pre-COVID, COVID and post-COVID periods. The 2010–2020 records are labelled by a new protocol: a script sends each request to a pinned model with a saved prompt, two independent readers rate every record, and a third reading adjudicates each disagreement. The 2021–2026 labels came from one reader per record with targeted cross-review, and they stay as recorded. We accept that the two sides of the comparison were labelled differently, and we measure the difference with a bridge sample: 200 already-labelled records from each earlier pass, labelled again without sight of the recorded labels and scored against them.

## Considered options

- **Relabel the whole corpus with one protocol.** Cleaner for the comparison, but it would create a second set of labels that contradicts the published one, and the 4,920 recent ratings are fixed by rule.
- **Label 2010–2020 with the earlier single-reader protocol.** Consistent, but that protocol only re-reads records already rated high, so it removes over-calls and leaves under-calls. Its audit found none of the level 4 records in its reference sample.
- **Label 2010–2020 only, with no bridge.** Any difference in how strictly the new readers judge would appear as a difference between periods, and nothing in the result would show it.

## Consequences

- Every figure that compares periods is reported beside the bridge sample's drift. A difference between periods smaller than the measured drift is not a finding.
- The bridge sample holds only 2021–2026 records, so it cannot detect drift specific to older texts, including readers rating a launch by what the product later became.
- The labelling script calls a model; the build still does not. The build replays the saved ratings, as it does for the earlier evidence.
- Labelling ran as headless Claude Code sessions (`claude -p`) on the maintainer's Claude subscription. The maintainer chose not to pay for the Claude API separately. Each session is fresh, with no tools, settings, or project instructions. The script reads back the model that answered and saves it with every reading. The script can call the API instead (`--client api`), but no saved reading came from it.
- The earlier evidence does not record which model produced it. The new evidence records the model and prompt for every reading.
