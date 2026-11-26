# The repository is public

The repository is public on GitHub at `tobyhede/aws-trend-explorer`, including the saved announcement text in the database, the exports and the review evidence. ADR 0001 kept the repository private because the AWS Site Terms reserve all rights in that text. The maintainer decided on 27 November 2026 that holding it here counts as fair use of public material: the announcements are published openly by AWS, and the repository keeps them as the evidence behind the classifications, with a link to each source. This is the maintainer's judgment, not legal advice and not a permission from AWS.

## Consequences

- This replaces only the part of ADR 0001 that kept the repository private. The public dataset and the hosted explorer still omit the text, and `verify.py` and `hosted/check_site.py` still enforce that.
- Anyone can now read the saved text and the raw review evidence in the repository, although the hosted explorer does not publish them.
- If AWS objects, the response is to make the repository private again or remove the text from its history.
