AWS directory snapshot: 2010–2020

This directory freezes what the AWS directory API (whats-new-v2) listed for the years 2010 to 2020 on the collection date, 27 November 2026. It is evidence, not generated output: do not edit or replace the raw files.

Files
- raw/<year>_p<page>.json: each API response saved byte for byte. Pages hold up to 2,000 records, the largest size the API answers; 2020 needs two pages.
- manifest.json: for each raw file, the request URL, collection date, size and SHA-256.

Counts on 27 November 2026
The year tags listed 8,423 records. Two of them, listed under the 2016 tag, are dated 2026 and are set aside: they are reported by early_collect.misdated() and are not part of the 2010–2020 records. One is already in the 2021–2026 corpus; the other is dated after its 28 October cutoff.

Year  Records
2010  66
2011  82
2012  91
2013  185
2014  295
2015  452
2016  640
2017  1,023
2018  1,433
2019  1,860
2020  2,294
Total 8,421

Coverage means what the API listed on the collection date. Posts the API no longer lists are absent; early_coverage.py measures that gap against the Internet Archive.

Commands, from the repository root
- Check, offline: .venv/bin/python product_change/early_collect.py check
- Collect: .venv/bin/python product_change/early_collect.py collect
  A rerun skips pages already saved. Collection uses a generic client name and waits 3 seconds between requests. The 2021–2026 corpus is not collected again.

Parsing (early_collect.parse) reads only these files. Each record has the corpus fields: the text is the summary and body with tags replaced by spaces, entities decoded and whitespace collapsed; service is the product tags sorted and joined with '; ', or unknown; the retired, unassessed and earlier-label columns are null. Checked against 200 stored 2021 records, the parser reproduced 199 exactly; the other differs only because AWS has since lowercased one product tag.
