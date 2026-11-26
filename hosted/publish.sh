#!/bin/sh
# Publish the hosted explorer to Cloudflare Pages by direct upload. Manual by design: nothing deploys automatically.
#
#   PAGES_PROJECT=<cloudflare-pages-project> hosted/publish.sh
#
# Runs the release check, the counting check and the upload-set check, then uploads hosted/site/ and nothing else.
set -eu
cd "$(dirname "$0")/.."
: "${PAGES_PROJECT:?Set PAGES_PROJECT to the Cloudflare Pages project name}"
.venv/bin/python product_change/verify.py
node hosted/check.mjs
.venv/bin/python hosted/check_site.py
npx --yes wrangler@4 pages deploy hosted/site --project-name "$PAGES_PROJECT" --branch main
