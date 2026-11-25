# Spec: hosted explorer and public dataset

**Status:** ready-for-agent

Vocabulary follows `GLOSSARY.md`. Decisions follow ADR 0001 (the public dataset omits saved announcement text) and ADR 0002 (the hosted explorer counts in plain JavaScript).

## Problem Statement

The classified AWS announcement corpus can only be explored by someone who receives the release bundle, installs Python and runs the local explorer. Nobody can be sent a link. The release bundle also cannot be published as it stands, because it contains saved announcement text that the AWS Site Terms do not permit us to republish.

## Solution

A hosted explorer: a public, static site that runs entirely in the visitor's browser and presents one frozen release. It reads a public dataset, which is the release's records without saved announcement text, published as a single dated file. The same file is the download for anyone who wants deeper analysis in their own tools. The local explorer and the release bundle are unchanged.

## User Stories

1. As a visitor, I want to open a link and see the charts without installing anything, so that I can explore the data immediately.
2. As a visitor, I want to see how many announcements the release contains and its collection cutoff, so that I know what period the data covers.
3. As a visitor, I want an annual table of announcements by magnitude level over the matched period, so that I can compare years fairly.
4. As a visitor, I want in-scale totals and year-on-year change for the matched period, so that I can see the overall trend.
5. As a visitor, I want a monthly chart by magnitude level, so that I can see how publication activity moves within and across years.
6. As a visitor, I want to switch the monthly chart between counts and shares, so that I can separate volume from composition.
7. As a visitor, I want the partial final month and year marked, so that I do not mistake a partial period for a decline.
8. As a visitor, I want to filter by release type, so that I can look at one kind of announcement.
9. As a visitor, I want to filter by service, so that I can follow one AWS service.
10. As a visitor, I want to filter by enhancement facet, so that I can follow one kind of enhancement.
11. As a visitor, I want to search titles and reasons, so that I can find announcements about a topic.
12. As a visitor, I want to be told that search covers titles and reasons only, so that I understand why a term from an announcement body finds nothing.
13. As a visitor, I want to select a chart bar or table cell and see the records behind it, so that I can check what a count is made of.
14. As a visitor, I want each record to show its date, title, services, magnitude level and reason, so that I can judge the classification.
15. As a visitor, I want each record to link to the official AWS announcement, so that I can read the source.
16. As a visitor, I want to page through long record lists, so that the page stays responsive.
17. As a visitor, I want to export the filtered records as CSV, so that I can work with a subset.
18. As a visitor, I want a short limits statement above the charts, so that I know the labels are AI judgments and rare-category trends are provisional before I read a chart.
19. As a visitor, I want to read the classification method, so that I understand what each magnitude level means.
20. As a visitor, I want to read the audit reports, so that I can judge how far to trust the labels.
21. As a visitor, I want a data guide for the public dataset, so that I can interpret each field and total correctly.
22. As a visitor using a keyboard or screen reader, I want charts and tables to be operable and labelled, so that I can use the site without a mouse or sight of the chart.
23. As a visitor, I want the site to set no cookies and load no third-party scripts, so that my visit is not tracked.
24. As an analyst, I want to download the whole public dataset as one file, so that I can run my own queries.
25. As an analyst, I want the file to keep its column types, so that magnitude levels are read as text and dates as dates.
26. As an analyst, I want the file name to carry the release date, so that I can cite exactly which data I used.
27. As an analyst, I want earlier releases to stay at their addresses, so that a citation keeps working after a new release.
28. As an analyst, I want a stated licence for the classifications and reasons, so that I know I may reuse them with attribution.
29. As an analyst, I want it stated that titles and linked pages remain AWS's, so that I do not assume the licence covers them.
30. As a reader, I want a statement that the site is not affiliated with or endorsed by AWS, so that I do not mistake it for an AWS publication.
31. As the maintainer, I want the public dataset built from the database by one command, so that it cannot drift from the release.
32. As the maintainer, I want the release check to fail if the public dataset contains announcement text, so that the text cannot be published by accident.
33. As the maintainer, I want the release check to confirm the public dataset has every record, so that the hosted explorer and the release bundle agree.
34. As the maintainer, I want the hosted explorer's counts checked against the released aggregate files, so that its JavaScript counting matches the verified Python counting.
35. As the maintainer, I want the release bundle's reproduction steps to keep needing only Python, so that recipients are unaffected.
36. As the maintainer, I want to publish with one command I run myself, so that nothing goes public before the release is checked.
37. As the maintainer, I want the repository to stay private, so that the saved announcement text is not published through source control.
38. As a release bundle recipient, I want the public dataset included in the bundle, so that I can reproduce it with everything else.
39. As a release bundle recipient, I want the local explorer to behave exactly as before, so that the verified release is not disturbed.

## Implementation Decisions

- **Public dataset.** One Parquet file per release, named with the release date. It holds nine fields: announcement date, title, service tags, release type, enhancement facets, product-change level, product-change reason, product-change basis and source URL. It omits saved announcement text, primary scope and title stage. It is compressed with a codec the page's Parquet reader supports without extra code; confirm which codecs that is before choosing.
- **Public dataset builder.** A new script in the product-change pipeline writes the public dataset from the database after the build step. It replays nothing and classifies nothing; it selects fields.
- **Counting module.** One JavaScript module holds all filtering and counting for the hosted explorer and touches no page elements. Its interface takes the records and a filter set and returns the annual matched-period counts, monthly counts, breakdowns and the selected records. It applies the same rules as the local explorer: matched period of 1 January to 28 October, in-scale totals that include needs-review and exclude outside-scale, shares divided by all filtered announcements, and multi-valued service and facet fields.
- **Page.** Plain HTML and JavaScript modules with no bundler, package install or content delivery network. A pinned copy of a small Parquet reader is checked into the repository. The page loads the public dataset once and holds it in memory.
- **Measures shown.** The current product-change measure only, with release type, service and facet filters. The retired magnitude and architecture measures and the scope views are not shown.
- **Search.** Case-insensitive substring match over title and reason, with a visible note that announcement bodies are not searched.
- **Supporting pages.** The method page, the historical audit report and the fresh-sample audit report are published after confirming they contain no excerpts of announcement text. The earlier 120-record review and all raw review evidence are not published. A data guide and release notes are published in versions limited to the nine public fields.
- **Statements on the page.** A limits statement of at most four lines above the charts; a CC BY 4.0 licence for classifications and reasons; a statement that titles and linked pages remain AWS's; a statement of non-affiliation with AWS; the release date and collection cutoff.
- **Hosting.** Cloudflare Pages by direct upload of the hosted explorer's files, on a subdomain of a personal domain. Publishing is one manual command. Earlier public dataset files remain at their dated addresses. No analytics, cookies or third-party requests.
- **Release bundle.** The packaging step includes the public dataset and leaves out the hosted explorer's source. The local explorer, its server and its page are not modified.
- **Repository.** Stays private. The hosted explorer's source lives in its own directory, and only that directory's publishable files are deployed.

## Testing Decisions

A good test here checks a published number or a published file against the released, verified outputs. It does not check how the counting is written.

- **Seam 1: the public dataset file.** The existing release check gains assertions on the file: no announcement-text field, exactly the nine fields, every record present, unique source URLs, and levels, reasons and bases equal to the database. Prior art: the existing release check already compares the CSV and JSON exports with the database.
- **Seam 2: the counting module's interface.** A Node check loads the public dataset, runs the counting module and compares its results with the released aggregate files for the matched annual period, the monthly series and the per-service matched comparison. It also compares a small fixed set of filtered queries with the local explorer's summary results. Node is a development-only requirement; the release check stays Python-only.
- **Not automated.** Chart rendering, keyboard operation and the deployed site are checked by hand in a browser before each publication, as the release notes already record for the local explorer.

## Out of Scope

- DuckDB-Wasm or any SQL entry on the page.
- Publishing saved announcement text, or a search index built from it.
- Ongoing collection of new announcements, or classification outside the audited release process.
- Changes to the local explorer, the classifications, or the 25 November 2026 release bundle.
- The retired magnitude, architecture and scope measures.
- Sharing chart code between the local explorer and the hosted explorer.
- Automatic deployment, authentication or analytics.

## Further Notes

- **Open:** the personal domain and subdomain are not yet chosen. This blocks only the deployment ticket.
- The AWS Site Terms also exclude derivative use and automated data gathering. ADR 0001 records how the design limits that exposure; it is the maintainer's reading, not legal advice.
- Adding the public dataset to the release bundle adds one file to the recorded reproduction hashes at the next release. Check that the file is written identically on a repeat build before recording a hash.
- The record count, date bounds and 28 October cutoff are fixed values in the local explorer. The hosted explorer should read the cutoff and release date from one place, so a new release changes one value.
