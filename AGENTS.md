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

## Git workflow — branch from `develop`, not `main`

This repo's active integration branch is **`develop`** — that is where `main` is stale (it lags
`develop` by hundreds of commits, e.g. it predates the `pyproject.toml` dependency migration,
Django v6, and Postgres 18 upgrades) and is not a safe base for new work despite the name.

- Before creating any branch or PR here, confirm the actual default branch rather than assuming
  `main`: `gh repo view SEED-platform/seed --json defaultBranchRef` (or check
  `git remote show origin` under "HEAD branch"). As of this writing it is `develop`.
- Always branch from an up-to-date `origin/develop` (`git fetch origin develop && git checkout -b
  <branch> origin/develop`), not from a possibly-stale local `main`. A local `main` that hasn't
  been pulled recently can be far behind without any error or warning — branching from it silently
  drags a huge, unrelated diff into your PR (e.g. files that look "deleted" simply because your
  stale base never had them).
- After pushing, verify the PR actually landed with the base you expect and a minimal diff:
  `gh pr view <number> --json baseRefName,additions,deletions,changedFiles`. `gh pr create` targets
  the repo's *default* branch automatically, which may silently differ from whatever local branch
  you happened to branch from.
- This guidance is specific to **this** repo (`SEED-platform/seed`). The `ng_seed/seed-angular`
  submodule's default branch is `main` — verify independently there rather than assuming the same
  convention applies, since the two repos can (and currently do) differ.

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
