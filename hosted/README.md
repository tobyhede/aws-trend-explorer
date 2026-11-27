# Hosted explorer

The public viewer for one frozen release. It runs entirely in the visitor's browser and reads the public dataset, which holds no saved announcement text. See `GLOSSARY.md`, `docs/adr/0001` and `docs/adr/0002` for the terms and decisions.

This directory is not part of the release bundle. Only `site/` is ever uploaded.

## Layout

| Path | Purpose |
| --- | --- |
| `site/` | Exactly the files that are published. |
| `site/release.js` | The one place for the release date, first date and collection cutoff. |
| `site/counting.js` | All filtering and counting. Touches no page elements. |
| `site/app.js`, `site/index.html`, `site/site.css` | The page. |
| `site/data/` | One dated public dataset per release. Earlier files stay here so their addresses keep working. |
| `site/vendor/hyparquet/` | Pinned copy of hyparquet 1.33.2 (MIT), the Parquet reader. `node.js` is left out because the browser does not need it. |
| `site/_headers` | Cloudflare Pages response headers: content security policy, no referrer, long cache for dated data. |
| `pages/` | The public data guide and release notes, limited to the nine public fields. |
| `pages.py` | Writes the five supporting pages into `site/`. |
| `check.mjs`, `local_summaries.py` | Check the counting module against the released aggregates and the local explorer. |
| `check_site.py` | Checks the upload set before publishing. |
| `publish.sh` | The one manual publish command. |

## View it

```sh
python3 -m http.server -d hosted/site 8766
```

Open http://127.0.0.1:8766. Any static file server works. Opening `index.html` as a file does not, because browsers do not load JavaScript modules from `file:` addresses.

## Check it

Run from the repository root. Node 22 or later is needed for development only; nothing is installed.

```sh
.venv/bin/python product_change/verify.py   # the public dataset: nine fields, every record, no announcement text
node hosted/check.mjs                       # JavaScript counts equal matched.csv, monthly.csv, service_matched.csv and serve.py summaries
.venv/bin/python hosted/check_site.py       # the upload set: no announcement text, no third-party requests, pages current, links resolve
```

Chart rendering, keyboard operation and the deployed site are not automated. Before each publication, check by hand in a browser:

- the annual table and monthly chart draw, and the share view sums to 100%;
- each filter and the search recalculate everything, and Clear filters restores 22,588;
- selecting a table count or a chart segment lists exactly that many records, by mouse and by keyboard (Tab into the chart, arrow keys, Enter);
- record titles open the AWS announcement; paging and CSV export work;
- the Parquet download and every supporting page open;
- on the deployed site, the browser's network panel shows requests to the site's own host only, and no cookies are set.

## Publish

Publishing is manual. Nothing deploys automatically, and no analytics are enabled.

```sh
PAGES_PROJECT=aws-whats-new hosted/publish.sh
```

The site's address is https://aws-whats-new.tobyhede.com, served by the Cloudflare Pages project `aws-whats-new`.

The script runs the three checks above and then uploads `hosted/site/` to Cloudflare Pages with Wrangler. It needs a Cloudflare login (`npx wrangler login`).

First publish only:

1. Create the project: `npx wrangler@4 pages project create aws-whats-new --production-branch main`.
2. Run the publish command.
3. In the Cloudflare dashboard, open Workers & Pages, then `aws-whats-new`, then Custom domains, and add `aws-whats-new.tobyhede.com`. Cloudflare adds the DNS record and the certificate.

Do not enable Cloudflare Web Analytics on the project: it injects a third-party script.

A direct upload replaces the whole site, so a dated dataset stays at its address only while its file stays in `site/data/`. Never delete an earlier release's file.

## Make a new release

1. Finish and verify the release in `product_change/` first.
2. Set the new release date and cutoff in `product_change/public_dataset.py` and in `site/release.js`, and the download link in `site/index.html`.
3. Run `product_change/public_dataset.py`. It writes the new dated file and copies it into `site/data/` beside the earlier ones.
4. Update `pages/release-notes.html` and, if fields or rules changed, `pages/data-guide.html`. Run `hosted/pages.py`.
5. Run the three checks, check by hand, then publish.

`pages.py` copies the method page and the two audit reports from the release. It stops if a source report has changed in a way its link replacements do not expect; review the new report for announcement text before adjusting them.
