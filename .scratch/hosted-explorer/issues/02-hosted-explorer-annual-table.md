# 02: Hosted explorer shows the annual matched-period table

**What to build:** A visitor opens the hosted explorer's page in a browser and sees the total number of announcements, the release date and collection cutoff, and a table of announcements by magnitude level for the matched period in each year, with in-scale totals and year-on-year change. The page reads the public dataset directly and makes no other data requests. This is the first end-to-end path: file, reader, counting module, page, check.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The page is plain HTML and JavaScript modules, with no bundler, package install or content delivery network
- [ ] A pinned copy of a small Parquet reader is checked into the repository and loads the public dataset
- [ ] All counting lives in one module that touches no page elements
- [ ] The annual table uses the matched period, 1 January to 28 October, in every year
- [ ] In-scale totals include needs-review and exclude outside-scale
- [ ] The release date and collection cutoff come from one place
- [ ] A Node check runs the counting module on the public dataset and matches the released matched-period aggregate file exactly
- [ ] The page works when served by any static file server
