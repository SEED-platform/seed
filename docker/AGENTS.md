# Container and Proxy Agent Guide

This guide adds container instructions to the [root guide](../AGENTS.md).
It applies under `docker/`; the root guide also directs related Dockerfile,
Compose, CI image-build, and compression-settings work here.

## Builds

- Production `Dockerfile` ends in `runtime`; `Dockerfile-dev` ends in `dev` and
  retains development tools. BuildKit/cache mounts are required. The build
  context is the repository root; images keep `/seed` as the Django root, holding
  the contents of `backend/` plus `docker/` and the Angular build from `frontend/`.
- Copy `backend/.python-version` before Python-install layers and
  manifests/lockfiles before dependency-install layers to preserve correct cache
  invalidation.
- CI builds ARM as well as x86 images. Preserve support for both architectures.

```sh
docker buildx build --progress=plain --file Dockerfile --target runtime --tag seedplatform/seed:local --load .
docker buildx build --progress=plain --file Dockerfile-dev --target dev --tag seedplatform/seed:dev --load .
```

## Startup, Static Assets, and Proxy Headers

- Production startup uses Django collect/compress. Sass is invoked via Node and
  its installed script, not a runtime pnpm/npx CLI.
- Check `backend/config/settings/common.py`, `docker/start_hypercorn_docker.sh`, and
  `docker/nginx/` together when changing compression or asset delivery.
- Preserve CSP on HTML responses and the referrer policy needed by
  OpenStreetMap tiles in both UIs.

Further reference: [container notes](README.md) and
[Docker setup](../docs/source/setup_docker.rst).
