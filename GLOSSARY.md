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
The viewer a recipient runs on their own computer from the release bundle, with access to every field including saved announcement text.
_Avoid_: Explorer (unqualified), server, Python explorer

**Hosted explorer**:
The public viewer that runs entirely in a visitor's browser and presents a frozen release without saved announcement text.
_Avoid_: Explorer (unqualified), WASM version, interactive version, web app
