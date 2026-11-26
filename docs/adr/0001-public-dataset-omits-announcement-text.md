# The public dataset omits saved announcement text

The AWS Site Terms (last updated 4 June 2025) reserve all rights in announcement text and give no attribution-based permission to republish it. The public dataset and the hosted explorer therefore carry only the date, title, service tags, classifications, our own reasons and bases, and the source URL for each record. The saved text stays in the release bundle. This ADR first kept the repository private because it contains that text; ADR 0004 replaces that part.

## Consequences

- Search in the hosted explorer covers title and reason only, so it can return fewer records than the local explorer for the same term.
- A search index built from the text was rejected, because it would still distribute a derivative of the text.
- Our classifications and reasons are offered under CC BY 4.0. Titles and linked pages remain AWS's and are outside that licence.
- The hosted explorer is published personally, not under a company name, and states that it is not affiliated with or endorsed by AWS.
