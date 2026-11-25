# 07: Release bundle includes the public dataset

**What to build:** Packaging a release puts the public dataset in the release bundle and leaves the hosted explorer's source out. The reproduction and repository guidance describe the new build step and the hosted check.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The packaging step includes the public dataset and excludes the hosted explorer's directory
- [ ] The packaging step's own content check passes
- [ ] The reproduction guide lists the public dataset builder in the rebuild order
- [ ] The repository guidance for agents describes the hosted explorer, the public dataset, the Node check and the rule that the repository stays private
- [ ] The local explorer, its server and its page are unchanged
- [ ] The recorded reproduction hashes are not edited; adding the public dataset's hash is noted for the next release
