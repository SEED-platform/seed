# SEED Platform Agent Guide

SEED manages organization-scoped building and tax-lot inventories, imports,
meter readings, and energy analyses. Its Django/DRF backend uses PostgreSQL with
PostGIS/TimescaleDB and Celery/Redis; two frontends share the backend and APIs.

This file applies to the SEED repository. Nested guides add area-specific
instructions; read the relevant guides below before working in those areas,
even when starting a session at the repository root. Treat configuration files
and executable code as the source of truth when older documentation disagrees.
Paths and commands in these guides are relative to the repository root unless
explicitly noted otherwise.

## Start Here

- Run `git status --short --branch` before editing. Preserve existing changes;
  do not switch branches, reset files, or update submodule pointers implicitly.
- Read the nearest implementation and its tests before changing behavior. Use
  the map below to avoid searching the entire repository unnecessarily.
- Check `.python-version`, `pyproject.toml`, `uv.lock`, and `package.json` for
  toolchain and dependency versions; do not infer them from an older README.
- Never commit or print credentials from `.env`, `local_untracked.py`, API test
  user files, or service configuration. Use the checked-in `.dist` for examples.
- Confirm database targets before running migrations. Obtain explicit approval
  for destructive commands (flush, reset, drop, restore) or changes to shared or
  production databases; ordinary tests should use disposable test databases.

## Scoped Guides and Entry Points

| Area                 | Guide and entry points                                                                                                                                                                                                                         |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Django backend       | [seed/AGENTS.md](seed/AGENTS.md): API/model/import map, backend invariants, tests, and migrations. Also read it for `config/settings/`, `config/urls.py`, `manage.py`, and `ng_seed/views.py`.                                                 |
| Legacy frontend      | [seed/static/seed/AGENTS.md](seed/static/seed/AGENTS.md): AngularJS routes, controllers, services, and tests. Also read it for `seed/templates/` and `seed/landing/static/`.                                                                   |
| Containers and proxy | [docker/AGENTS.md](docker/AGENTS.md): builds, startup, static assets, and nginx. Also read it for root `Dockerfile*`, `docker-compose*.yml`, CI image builds in `.github/workflows/`, and compression settings in `config/settings/common.py`. |
| New Angular frontend | Separate `ng_seed/seed-angular/` git submodule; follow its own guides as described below.                                                                                                                                                      |

The links above explicitly cover related work outside each guide's directory;
a nested file alone does not govern sibling or parent directories. Keep shared
rules here and specialized guidance in the relevant guide, without duplication.

## Setup and Local Commands

Use `uv` for Python and the pnpm version declared by `package.json`.

```sh
git submodule update --init ng_seed/seed-angular
uv sync --locked
pnpm install --frozen-lockfile
```

- Both dev and test settings require `config/settings/local_untracked.py`. If
  missing, create it from `config/settings/local_untracked.py.dist` and configure
  the local services. Never overwrite an existing local configuration.
- Django needs PostgreSQL/PostGIS and native GDAL/GEOS libraries. SQLite is not
  a substitute for this application's tests. See
  [local setup](docs/source/setup_osx.rst) and
  [Docker setup](docs/source/setup_docker.rst). For native Windows development,
  GDAL/GEOS must be discoverable through the environment or the library-path
  settings; Python dependencies alone do not provide these native libraries.
- Redis supports caching and Celery. Basic local development can use eager
  Celery tasks as described in [README.md](README.md); asynchronous API workflows
  require a real worker. Local settings can override the test defaults too.
- The root pnpm workspace includes `vendors` and the Angular submodule, with
  separate lockfiles. Check `pnpm-workspace.yaml` before changing overrides or
  installing dependencies in only one workspace. Root overrides take precedence
  over the nested Angular workspace's overrides during a root install.

After configuring services and initializing a confirmed local database using
the setup docs, start the development server:

```sh
uv run python manage.py runserver --settings=config.settings.dev
```

## Tests and Quality Checks

Prefer a focused test first, then broaden coverage for shared behavior. The
backend and legacy frontend guides contain their test commands and service
requirements; new Angular tests belong to the submodule.

```sh
uv run pre-commit run --files path/to/changed_file.py
uv run pre-commit run --all-files
uv run pre-commit run ty --all-files
pnpm lint
```

- Pre-commit runs Ruff and ty. Use the hook to get the pinned type checker. Local
  Prettier hooks need root `node_modules` installed. `pnpm lint` additionally runs
  ESLint/Stylelint and template formatting checks; a passing pre-commit run does not
  replace it for frontend changes.
- `--all-files` covers tracked files; explicitly pass new, untracked files too.
  Review formatter changes and rerun hooks until clean. Fix real issues before
  adding suppressions; keep unavoidable framework exceptions narrow and explained.
- CI's relevant quality environments are `uv run tox -e precommit` and
  `uv run tox -e lint`. Consult `tox.ini` and `.github/workflows/ci.yml` before
  running other environments. Standalone management commands such as `flush_db`
  operate on the configured database; selecting test settings alone does not
  switch them to a test database.

## Two Frontends and Migration Boundaries

- The **legacy AngularJS app** serves `/app/` from `seed/static/seed/`.
- The **new Angular app** serves `/ng-app/` and lives in the separate
  `ng_seed/seed-angular` repository. Read its `DEVELOPER.md`,
  `.github/copilot-instructions.md`, and any nested `AGENTS.md` before editing.
  If `MIGRATION.md` exists in that checkout, read it first for migration work;
  it is not present in every submodule revision.
- Both UIs are live. Do not assume implementing an Angular page redirects users
  away from AngularJS. Do not remove or change legacy behavior during a migration
  unless explicitly requested. Shared API changes may affect both clients.
- Commit/review Angular changes in the submodule repository; the parent only
  records its commit pointer. Do not accidentally advance that pointer while
  working on the backend. The submodule tracks `main`, independently of SEED.

## Dependency Changes

Review upstream changelogs/migration notes and actual usage. Update
`pyproject.toml` and `uv.lock` together, e.g.
`uv lock --upgrade-package <package>`, then `uv sync --locked` and
`uv lock --check`. Do not bypass transitive constraints silently; document any
tested override and when it can be removed.

## Conventions and Git Workflow

- Let `ruff.toml`, `ty.toml`, `.pre-commit-config.yaml`, and the frontend configs
  define formatting/checks. Prefer existing local helpers over new abstractions.
- New project Python files start with this header (historical migrations are not
  a reason to add unrelated header churn):

```python
"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
```

- SEED's integration/default branch is `develop`; do not assume `main` is the
  base. When asked to create a branch/PR, confirm with
  `gh repo view SEED-platform/seed --json defaultBranchRef`, fetch the intended
  base, and branch from up-to-date `origin/develop`, preserving current work.
  Verify the PR base and diff after creation. Verify the Angular repository's
  default branch separately.
- Keep fixes scoped; avoid generated assets, lockfile churn, migrations, or
  unrelated refactors unless required by the task. Report commands actually run,
  results, and anything unverified or blocked, including missing service credentials.

Further reference: [README.md](README.md),
[developer resources](docs/source/developer_resources.rst), and
[container notes](docker/README.md). Keep this guide focused on durable entry
points and pitfalls rather than duplicating those manuals or dependency versions.
