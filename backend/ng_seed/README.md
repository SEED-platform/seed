# ng_seed

This Django app serves the Angular UI from `frontend/` at `/ng-app/`. It reads the build output that
`pnpm watch` or `pnpm build` writes to `collected_static/ng-app`. See
[`frontend/README.md`](../../frontend/README.md) for running the Angular app, either through Django
or with Angular's hot-reloading development server.
