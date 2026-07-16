# SEED-Angular

This documentation describes the process of setting up and running the new SEED Angular UI alongside the AngularJS UI.

All the following commands assume that this location is your current working directory (`cd ng_seed/seed-angular`).

There are two supported local development workflows:

- Use Angular's development server at [http://localhost:4200](http://localhost:4200) for hot-reloading frontend work.
- Use Django at [http://localhost:8000/ng-app/](http://localhost:8000/ng-app/) when testing the Angular app as it is served by SEED.

The Django route only works after Angular has written files to `collected_static/ng-app`.

### Install dependencies

```bash
pnpm i
```

### Run in development

**From Angular with hot-reloading:**

```bash
pnpm start
```

Then browse to [http://localhost:4200](http://localhost:4200).

The Angular development server proxies `/api/` and `/media/` requests to Django. By default it expects Django at `http://127.0.0.1:8000`. If Django is running somewhere else, create `.env` in this directory and set:

```bash
SEED_HOST=http://127.0.0.1:8000
```

**From Django:**

```bash
pnpm watch
```

Keep this command running in a separate terminal while Django is running. It builds the Angular app in development mode and watches for changes. Then browse to [http://localhost:8000/ng-app/](http://localhost:8000/ng-app/).

### Build for production

```bash
pnpm build
```

This writes the production build to `../../collected_static/ng-app`.

### Troubleshooting

If Django returns this error:

```text
Page not found (404)
seed-angular static files not found
```

then `collected_static/ng-app/index.html` does not exist yet. From `ng_seed/seed-angular`, run one of:

```bash
pnpm watch
pnpm build
```

Use `pnpm watch` for local development through Django. Use `pnpm build` when you only need a one-time production build.

## Submodule commands

This branch adds a git submodule for linking the seed-angular repo.

- When switching to this branch run `git submodule update --init`
- When you need to update the submodule to the latest commit from the seed-angular repo: `git submodule update --remote`
  or `git pull origin task/angular-20`
  - From the SEED root, you can also run `git submodule update --remote ng_seed/seed-angular`
