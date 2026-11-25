# 08: Publish the hosted explorer

**What to build:** The maintainer runs one command and the hosted explorer is live on a subdomain of a personal domain, served by Cloudflare Pages from a direct upload. The dated public dataset is at a stable address, and the site sets no cookies and makes no third-party requests.

**Blocked by:** 03, 04, 05, 06, and the maintainer's choice of domain and subdomain

**Status:** needs-info

- [ ] The maintainer has named the domain and subdomain
- [ ] One documented command uploads only the hosted explorer's publishable files
- [ ] Nothing containing saved announcement text is uploaded; the upload set is checked for this before publishing
- [ ] The public dataset is served at an address that includes the release date, and the layout keeps earlier files in place at later releases
- [ ] The deployed site loads with no cookies set and no requests to other hosts
- [ ] Charts, filters, drill-down and downloads are checked by hand in a browser on the deployed site
- [ ] Publishing is manual; no automatic deployment is configured
