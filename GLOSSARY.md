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

### Viewers

**Local explorer**:
The explorer page run on a recipient's own computer through `serve.py` from the release bundle. It is the same page as the hosted explorer, and it also shows each record's saved announcement text.
_Avoid_: Explorer (unqualified), server, Python explorer

**Hosted explorer**:
The explorer page as published: it runs entirely in a visitor's browser and presents a frozen release without saved announcement text. There is one explorer page; the local and hosted explorers are two ways of running it.
_Avoid_: Explorer (unqualified), WASM version, interactive version, web app
