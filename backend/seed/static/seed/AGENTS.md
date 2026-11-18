# Legacy AngularJS Agent Guide

This guide adds legacy frontend instructions to the
[root guide](../../../AGENTS.md) and [backend guide](../../AGENTS.md).
It covers the assets under this directory; the root guide also directs template
and landing-page work here as a shared reference.

## Entry Points

- The legacy app serves `/app/`. Routes and modules live in
  `seed/static/seed/js/seed.js`; behavior lives in `js/controllers/` and
  `js/services/` beneath `seed/static/seed/`, and views live in `partials/`.
- Django script loading lives in `seed/templates/seed/_scripts.html`.
  Keep AngularJS injection arrays aligned with function parameters when adding
  or removing services.
- The new Angular app is a separate submodule, not part of this directory.
  Follow the root guide's migration boundaries when working across the two UIs.

## Checks

```sh
pnpm lint
pnpm test
```

- Root `pnpm test` runs legacy Jasmine tests through Puppeteer/Chrome. Django
  must already serve `/angular_js_tests/` with debug enabled on localhost:8000
  (preferred) or localhost:80 (fallback).
- `pnpm lint` covers ESLint, Stylelint, and template formatting; pre-commit alone
  does not replace it. Run the relevant checks for scripts, styles, and partials.
- For tile or browser-security issues, also read the
  [Docker/proxy guide](../../../docker/AGENTS.md). Proxy headers affect both UIs.
