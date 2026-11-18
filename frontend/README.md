# SEED Angular

## Prerequisites
- Node v24.15+ (24.x) or v26+
- [pnpm](https://pnpm.io/installation) v12+ (the exact version is pinned in `package.json`)

## Setup
1. Install a supported Node version (see Prerequisites)
2. Install pnpm globally: `npm i -g pnpm`
3. Install the project dependencies: `pnpm i`
4. Create a `.env` file in the root of the project directory that matches the format of [`.env.example`](.env.example)
   1. Add your Lokalise API key
   2. If your SEED instance is running at a location other than `http://127.0.0.1:8000`, set `SEED_HOST` in the `.env` file

## Actions

### Run with Angular hot reloading
1. Run `pnpm start`
2. Browse to [localhost:4200](http://localhost:4200)

The Angular development server proxies `/api/` and `/media/` requests to Django. By default it expects Django at `http://127.0.0.1:8000`.

### Run through Django
1. Start Django in one terminal
2. Run `pnpm watch` in this directory
3. Browse to [localhost:8000/ng-app/](http://localhost:8000/ng-app/)

Use `pnpm watch` while actively developing:
- Keeps running
- Rebuilds automatically on file save
- Best for local UI changes

Use `pnpm build` when you only need a one-time output:
- Runs once and exits
- Does not rebuild automatically
- Best for quick verification or production-like builds

Both commands write Angular output under `../../collected_static/ng-app`.
The Django `/ng-app/` route serves those files; it does not start the Angular development server.

If Django returns this error:

```text
Page not found (404)
seed-angular static files not found
```

follow this checklist:
1. In `ng_seed/seed-angular`, run `pnpm watch` (recommended for dev) or `pnpm build`.
2. Confirm Angular output exists under `../../collected_static/ng-app`.
3. If your output is under `../../collected_static/ng-app/browser/index.html` (instead of `../../collected_static/ng-app/index.html`) and Django still shows 404, your backend static-file lookup may only be checking the non-`browser` path.
4. If that happens, use the current backend static-file convention in your branch or update the backend lookup to support the `browser` subdirectory.

Tip: for everyday development through Django, keep `pnpm watch` running in a dedicated terminal.

### Lint
1. Run `pnpm lint`, or `pnpm lint:fix` to automatically fix issues

### Update Translations
1. Run `pnpm update-translations`

## Coding Standards
Refer to [DEVELOPER.md](DEVELOPER.md) for all coding standards and guidelines.
