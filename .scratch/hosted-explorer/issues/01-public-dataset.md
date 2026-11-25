# 01: Build and check the public dataset

**What to build:** One command writes the public dataset for the release: a single dated Parquet file holding every record with the nine public fields and no saved announcement text. The release check then fails if the file contains announcement text, lacks a record, or disagrees with the database.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Running the builder after the build step writes one Parquet file named with the release date
- [ ] The file has exactly nine fields: announcement date, title, service tags, release type, enhancement facets, product-change level, product-change reason, product-change basis, source URL
- [ ] Product-change level is stored as text and announcement date as a date
- [ ] The file's compression is one the chosen browser Parquet reader supports without extra code; the choice is confirmed against that reader's documentation
- [ ] The release check asserts: no announcement-text field, 14,167 records, unique source URLs, and levels, reasons and bases equal to the database
- [ ] The release check still passes with its existing final message, and still needs only Python
- [ ] Building twice produces an identical file, or the difference is recorded as a note for the next release's reproduction hashes
