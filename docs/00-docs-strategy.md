# Documentation Strategy — GitHub vs Google Drive

**Principle: GitHub is the single source of truth. Google Drive holds rendered copies and anything that isn't version-controlled text.**

This mirrors how large Finnish engineering organisations work: engineering docs live next to the code (ADRs and runbooks in repos), while governance material and stakeholder-facing documents circulate as Office files on Confluence/SharePoint/Drive.

## Division of responsibility

| Document | Master lives in | Drive gets |
|---|---|---|
| README, architecture, ADRs | GitHub (`docs/03-architecture/`) | — (technical, no Drive copy needed) |
| Project charter | GitHub (`docs/01-governance/`) | PDF/DOCX export at each baseline |
| Business case | GitHub (`docs/01-governance/`) | PDF/DOCX export |
| Risk register | GitHub (`docs/01-governance/`) | Optional Google Sheet for sortable columns |
| Product backlog | GitHub (`docs/02-planning/` + GitHub Issues) | — |
| Sprint plan & reviews | GitHub (`docs/02-planning/`) | — |
| Compliance notes | GitHub (`docs/04-compliance/`) | PDF export |
| Master Project Plan (combined) | Generated from repo docs | **DOCX — primary Drive artifact** |
| Meeting notes / scratch thinking | — | Google Docs (fast, informal) |
| Demo videos, screenshots, diagram sources | — | Drive (binaries don't belong in git) |
| Learning journal | Either | Google Doc is convenient for daily notes |

## Rules

1. **Never edit a Drive copy of a repo document.** Edit the Markdown, commit, re-export. A Drive copy that drifts from the repo is worse than no copy.
2. Every exported file carries a footer: version (git tag or commit short-hash) and export date.
3. Backlog *items* live as GitHub Issues; the backlog *document* explains structure and epics.
4. Drive folder structure mirrors the repo:

```
Google Drive: Petosvahti/
├── 01-Governance/        charter.pdf, business-case.pdf, master-project-plan.docx
├── 02-Meeting-notes/     Google Docs
├── 03-Compliance/        regulatory-context.pdf
├── 04-Media/             demo videos, diagram sources, screenshots
└── 05-Learning-journal/
```

## Versioning

- Docs follow the code's git flow: changes via commits with meaningful messages (`docs: update risk register after sprint 2 review`).
- Baseline moments (charter approval, end of each sprint) are git tags: `docs-baseline-s0`, `docs-baseline-s1`, …
- Exports to Drive happen at baselines only — not on every commit.
