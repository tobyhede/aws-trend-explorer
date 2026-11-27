# AWS announcement explorer

A classified corpus of AWS announcements, the review evidence behind the classifications, and the viewers that present them.

## Language

### Data

**Release bundle**:
The complete archive for one release: every record with saved announcement text, the review evidence, the analysis scripts and the local explorer.
_Avoid_: Archive, zip, package

**Public dataset**:
The records of one release without saved announcement text, published as a single dated file.
_Avoid_: Export, public export, download file

### Analysis

**Substantive output**:
The number of announcements in a period that record a product change above the routine levels, read together with the share of all announcements at each level. It is a proxy for shipped product change, not a measure of how well the organisation performed.
_Avoid_: Org performance, productivity, velocity

**Pre-COVID period**:
The calendar years 2010 to 2019.
_Avoid_: Before COVID, pre-pandemic

**COVID period**:
The calendar years 2020 and 2021, reported on their own and counted in neither of the other two periods.
_Avoid_: Pandemic years, transition

**Post-COVID period**:
The calendar years 2022 to 2026, the last of them partial.
_Avoid_: After COVID, post-pandemic

**Bridge sample**:
A random set of already-labelled records that a later group of readers labels again without seeing the recorded labels, to measure how far the two groups' judgments differ. It never changes a recorded label.
_Avoid_: Calibration set, relabel, overlap sample

### Viewers

**Local explorer**:
The explorer page run on a recipient's own computer through `serve.py` from the release bundle. It is the same page as the hosted explorer, and it also shows each record's saved announcement text.
_Avoid_: Explorer (unqualified), server, Python explorer

**Hosted explorer**:
The explorer page as published: it runs entirely in a visitor's browser and presents a frozen release without saved announcement text. There is one explorer page; the local and hosted explorers are two ways of running it.
_Avoid_: Explorer (unqualified), WASM version, interactive version, web app
