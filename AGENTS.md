# AGENTS.md

Orientation notes for AI agents working in the SEED Platform™ repo, specifically around the
**frontend migration** currently in progress. (This file intentionally does not attempt to
document the whole Django backend — only the frontend split relevant to migration work.)

## Two frontends, one backend

This Django repo currently serves **two separate single-page apps** side by side:

- **Legacy AngularJS 1.x app** — lives in-tree at `seed/static/seed/` and is served under `/app/`
  (see `seed.urls`, wired up in `config/urls.py`). Its route table (URL → template → controller)
  is `seed/static/seed/js/seed.js`; controllers are in `js/controllers/`, templates in `partials/`.
- **New Angular app** — lives in the `ng_seed/seed-angular` **git submodule**
  (https://github.com/SEED-platform/seed-angular), a separate repo with its own history. It's
  served under `/ng-app/` as a static SPA (`ng_seed/views.py::seed_angular` serves its
  `index.html` for any non-file request under that path). Because it's a submodule, changes to it
  are committed and reviewed in that repo, not here — `cd ng_seed/seed-angular` to work on it, and
  its own `.github/copilot-instructions.md` applies once you're inside that directory.

The end goal is to retire `seed/static/seed/` once every page has an equivalent in
`ng_seed/seed-angular`. Both apps currently run in parallel; there is no automatic redirect from
one to the other yet, so don't assume migrating a page's UI is enough to make it "live" — routing/
cutover is a separate decision.

## Migration work

If you're asked to migrate a page/feature from the legacy AngularJS app to the new Angular app:

1. Read `ng_seed/seed-angular/MIGRATION.md` first — it has the step-by-step playbook (how to find
   the legacy route/controller/partial, how to map it to the new app's structure and conventions,
   template conversion cheat sheet, translation reuse) and a tracked checklist of pages that still
   need to be ported.
2. Do the actual Angular work inside `ng_seed/seed-angular` (a separate git checkout/submodule),
   following that repo's own conventions in `DEVELOPER.md` and `.github/copilot-instructions.md`.
3. Don't delete or modify the legacy AngularJS source in `seed/static/seed/` as part of a
   migration change unless explicitly asked to — it keeps serving `/app/` traffic until the team
   decides to retire a given route.
