# Live-testing a page against a real backend (Playwright + seeded data)

`pnpm lint` and `pnpm build` only catch type/compile errors and template mistakes. They **cannot**
catch a missing ag-grid module registration, a wrong assumption about an API response's field
names, a route-param reactivity bug, or a CSS layout that only breaks with real data. For any
change that's interactive or backend-driven — a new page, a form, a grid, drag-and-drop, anything
that isn't a pure refactor/style change — treat lint + build as necessary but **not sufficient**.
Actually load the page in a browser against a live backend with real seeded data and click through
it with Playwright before calling the work done. This is what caught 4 real bugs in the Pairing
workflow migration that lint/build both missed (module registration, field-name assumptions, an
unpinned column, and a route-param staleness bug) — see PR that migrated `datasets/pairing` for a
worked example.

This doc is the recipe for standing up a throwaway backend + test data in this environment,
driving it with Playwright, and publishing the resulting screenshots to the PR, plus the gotchas
already discovered so you don't have to rediscover them.

## 1. Stand up an isolated backend

The Django backend lives in the parent `seed` repo (this app's repo is a git submodule of it). It
has a full docker-compose stack, but **don't reuse `docker-compose.dev.yml` as-is** — it bind-mounts
`./config:/seed/config/` from the host, which on a machine with a personal
`config/settings/local_untracked.py` (macOS `GDAL_LIBRARY_PATH`/`GEOS_LIBRARY_PATH` overrides, etc.)
gets mounted straight into the Linux container and crashes it. Compose also merges (concatenates)
`volumes:`/`ports:` lists across `-f` layered files rather than replacing them, so you can't
"unmount" it with an override file either. Write one standalone compose file instead:

```yaml
# /tmp/docker-compose.pairing-test.yml (adjust names/ports per feature)
services:
  db-postgres:
    container_name: seed_pt_postgres
    image: timescale/timescaledb-ha:pg18.3-ts2.26.4-oss
    environment:
      - POSTGRES_DB=seed
      - POSTGRES_USER=seed
      - POSTGRES_PASSWORD=super-secret-password
    volumes:
      - seed_pt_pgdata:/home/postgres/pgdata
  db-redis:
    container_name: seed_pt_redis
    image: redis:8-alpine
  web:
    container_name: seed_pt_web
    image: seedplatform/seed:develop
    # NOT `uv run hypercorn ...` — this image's `uv` CLI isn't on PATH, only the uv-managed
    # venv is. Call hypercorn directly from the venv (already on PATH).
    command: hypercorn config.asgi:seed --bind 0.0.0.0:80
    environment:
      - POSTGRES_DB=seed
      - POSTGRES_PORT=5432
      - POSTGRES_USER=seed
      - POSTGRES_PASSWORD=super-secret-password
      - SEED_ADMIN_USER=user@seed-platform.org
      - SEED_ADMIN_PASSWORD=super-secret-password
      - SEED_ADMIN_ORG=default
      - SECRET_KEY=ARQV8qGuJKH8sGnBf6ZeEdJQRKLTUhsvEcp8qG9X9sCPXvGLhdxqnNXpZcy6HEyf
      - DJANGO_SETTINGS_MODULE=config.settings.docker_dev
      - GOOGLE_RECAPTCHA_SITE_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
      - GOOGLE_RECAPTCHA_SECRET_KEY=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
    depends_on: [db-redis, db-postgres]
    volumes:
      - seed_pt_media:/seed/media
    ports:
      - "8010:80" # pick a free host port
volumes:
  seed_pt_pgdata:
    external: true
  seed_pt_media:
    external: true
```

```bash
docker volume create seed_pt_pgdata && docker volume create seed_pt_media
docker compose -p seed_pairing_test -f /tmp/docker-compose.pairing-test.yml up -d
docker exec seed_pt_web python manage.py migrate
docker exec seed_pt_web python manage.py create_default_user \
  --username=user@seed-platform.org --password=super-secret-password --organization="<org name>"
```

Use a **unique project name** (`-p`) and **unique volume/container names** per session so you
don't collide with (or destroy) another dev environment on a shared machine. Skip the
`web-celery` service unless the feature you're testing genuinely needs an async task
(mapping/matching/celery-backed exports) — pair/unpair-style CRUD doesn't.

## 2. Seed real test data

`manage.py create_and_load_sample_data` (the usual sample-data command) imports
`seed.test_helpers.fake`, which needs the `faker` package — **not installed in the runtime image**,
and the image has no `pip`/`uv` to install it with either. Don't fight this: create the handful of
records you actually need directly via `manage.py shell`, following the same model pattern that
command uses internally:

```python
# via: docker exec -i seed_pt_web python manage.py shell < script.py
from seed.lib.superperms.orgs.models import Organization
from seed.models import Cycle, Property, PropertyState, PropertyView, TaxLot, TaxLotState, TaxLotView, TaxLotProperty
from seed.data_importer.models import ImportRecord, ImportFile

org = Organization.objects.get(name="<org name>")
ali = org.root
cycle, _ = Cycle.objects.get_or_create(name="2020 Annual", organization=org, start=..., end=...)

pstate = PropertyState.objects.create(organization=org, address_line_1="111 Main St", raw_access_level_instance=ali)
prop = Property.objects.create(organization=org, access_level_instance=ali)
pview = PropertyView.objects.create(property=prop, cycle=cycle, state=pstate)
# ...same pattern for TaxLotState/TaxLot/TaxLotView...
TaxLotProperty.objects.get_or_create(property_view=pview, taxlot_view=tview, cycle=cycle)  # pairs them

# If the page needs an ImportFile: ImportRecord.super_organization must be set (separate from
# access_level_instance) or every v3 import_files endpoint 400s with "could not locate import
# file" — this field is easy to miss, it isn't on the obvious "org ownership" path.
import_record = ImportRecord.objects.create(name="Test Dataset", app="seed", access_level_instance=ali,
                                             super_organization=org, start_time=timezone.now())
ImportFile.objects.create(import_record=import_record, cycle=cycle, uploaded_filename="test.csv",
                           mapping_done=True, matching_done=True, num_rows=1)
```

Create **both paired and unpaired** (or matched/unmatched, empty/populated, etc.) records so you can
exercise both branches of whatever you're testing, not just the happy path.

## 3. Point the ng dev server at it and drive it with Playwright

```bash
echo "SEED_HOST=http://127.0.0.1:8010" > .env   # gitignored; matches your chosen host port
pnpm start                                       # ng serve, proxies /api to SEED_HOST
```

The app auth is JWT (`/api/token/`), not Django sessions, so just sign in through the real sign-in
page — no manual cookie/token wrangling needed. With the Playwright MCP tools:

1. `browser_navigate` to `http://localhost:4200/ng-app/sign-in`, `browser_fill_form` the
   email/password (+ the terms checkbox), `browser_click` "Sign in".
2. `browser_navigate` directly to the page/route you're testing.
3. `browser_snapshot` / `browser_take_screenshot` to inspect the rendered page, and
   `browser_console_messages` (level `error`, then `warning`) after every navigation — check both,
   not just for a clean exit code. A page can render with 0 visible issues and still have thrown
   errors that a fallback swallowed.
4. Exercise the actual interaction (drag-and-drop, form submit, filter/select changes, tab
   switches) with `browser_drag`/`browser_click`/`browser_fill_form`, and re-snapshot/screenshot
   after each one to confirm the UI actually changed, not just that no error was thrown.
5. If something looks wrong but the cause isn't obvious from the snapshot, use
   `browser_evaluate` to call the real API endpoint from the page's own context (reuse its auth)
   and inspect the raw JSON — this is how the Pairing migration found that the API suffixes field
   names with a unique column id (`address_line_1_11`), which a snapshot alone wouldn't reveal.

## 4. Put screenshots in the PR

A reviewer shouldn't have to stand up a backend themselves to see what a page looks like. Once the
feature is working end-to-end, capture a small set of `browser_take_screenshot` PNGs and embed them
in the PR description (not just described in prose):

- One screenshot of the **overall new page/form** in a normal, populated state.
- One or two screenshots **highlighting the new/notable interaction** specifically — e.g.
  mid-drag or right after a state-changing action (a row just paired/unpaired, a validation error
  showing, a save confirmation) — not just more of the same static view.

GitHub's real drag-and-drop "attach a file" feature (the one that produces
`github.com/user-attachments/...` URLs) is a private, browser-session-only upload endpoint — there's
no public API or `gh` command for it, and a `gh`-authenticated CLI session doesn't carry over to a
logged-in browser session, so it can't be scripted. **Gists don't work either** — `gh gist create`
(and the Gist API generally) only accepts text files: uploading a `.png` fails with
`binary file not supported`. Don't commit the PNGs to the repo/branch tree either — that pollutes
the feature's git history with binary review artifacts forever.

Instead, host them as **assets on a dedicated, clearly-labeled prerelease** (`gh release
create`/`upload` is a real public API, and release assets live outside any branch's tree — they
don't touch the repo's source history at all):

```bash
gh release create pr-<number>-screenshots \
  --title "PR #<number> review screenshots (not a version release)" \
  --notes "Temporary asset host for screenshots referenced in PR #<number>. Not a software release — safe to delete once the PR merges/closes." \
  --prerelease \
  --target <branch-tip-sha> \
  overview.png drag-pair.png
```

```markdown
![Pairing page](https://github.com/<owner>/<repo>/releases/download/pr-<number>-screenshots/overview.png)
![Drag-and-drop pairing in action](https://github.com/<owner>/<repo>/releases/download/pr-<number>-screenshots/drag-pair.png)
```

Update the PR body with `gh pr edit <number> --body-file <file>` (write the full new body to a
temp file first — `--body-file` replaces the whole description, it doesn't append). Delete the
prerelease (`gh release delete pr-<number>-screenshots --cleanup-tag`) once the PR is merged or
closed.

## 5. Clean up

The `.env` override, seed-data scripts, and any exploratory screenshots you didn't select for the
PR are throwaway verification infrastructure — none of it belongs in the branch, and (per step 4)
the ones you did select don't either; they live on the prerelease, not in git history.

```bash
rm .env  # restore whatever proxy config you had (or none)
docker compose -p <project> -f /tmp/docker-compose.<name>.yml down
docker volume rm <pgdata volume> <media volume>
rm /tmp/docker-compose.<name>.yml  # and any scratch seed-data scripts/unused screenshots
```

Verify with `docker ps -a` / `docker volume ls` that nothing you created is still around,
especially on a shared machine.
