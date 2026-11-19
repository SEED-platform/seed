# syntax=docker/dockerfile:1.7

ARG NGINX_LISTEN_OPTS
ARG UV_VERSION=0.13.9
# Registry for Docker Hub images. Defaults to Docker Hub; a build system can point it at a Docker Hub mirror.
ARG DOCKERHUB_REGISTRY=docker.io

# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nlr.gov>
# DESCRIPTION:      Production image with SEED Platform and runtime dependencies
# TO_BUILD_AND_RUN: docker compose build && docker compose up

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${DOCKERHUB_REGISTRY}/library/node:24-alpine AS build-base
COPY --from=uv /uv /uvx /bin/

WORKDIR /seed

COPY ./backend/.python-version /seed/.python-version

RUN --mount=type=cache,target=/root/.cache/uv \
    apk add --no-cache \
        g++ \
        git \
        make && \
    corepack enable && \
    uv python install && \
    python_path="$(uv python find)" && \
    ln -sf "${python_path}" /usr/local/bin/python3 && \
    ln -sf "${python_path}" /usr/local/bin/python

ENV PNPM_STORE_DIR="/pnpm/store" \
    npm_config_python="/usr/local/bin/python3" \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR="/opt/uv/python" \
    UV_PROJECT_ENVIRONMENT="/seed/.venv"
ENV PATH="/seed/.venv/bin:$PATH"

FROM build-base AS python-deps
RUN apk add --no-cache \
        alpine-sdk \
        bzip2-dev \
        cargo \
        gdal \
        gdal-dev \
        geos-dev \
        libffi-dev \
        libxml2-dev \
        libxslt-dev \
        linux-headers \
        musl-dev \
        ncurses-dev \
        libpq-dev \
        openssl-dev \
        pcre-dev \
        readline-dev \
        sqlite-dev \
        xz-dev \
        zlib-dev

COPY ./backend/pyproject.toml /seed/pyproject.toml
COPY ./backend/uv.lock /seed/uv.lock
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --managed-python --no-dev --no-install-project && \
    uv pip install supervisor==4.3.0

# The Angular app builds into ../backend/collected_static/ng-app (see frontend/angular.json)
FROM build-base AS frontend-build
ENV CI=true
WORKDIR /repo/frontend

COPY ./frontend/package.json ./frontend/pnpm-lock.yaml ./frontend/pnpm-workspace.yaml ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store,sharing=locked \
    pnpm install --frozen-lockfile --store-dir "${PNPM_STORE_DIR}" --config.confirmModulesPurge=false
COPY ./frontend ./
RUN ./node_modules/.bin/ng build

FROM build-base AS node-runtime-deps
ENV CI=true

COPY ./backend/package.json /seed/package.json
COPY ./backend/pnpm-lock.yaml /seed/pnpm-lock.yaml
COPY ./backend/pnpm-workspace.yaml /seed/pnpm-workspace.yaml
COPY ./backend/vendors/package.json /seed/vendors/package.json
COPY ./backend/vendors/pnpm-lock.yaml /seed/vendors/pnpm-lock.yaml
RUN --mount=type=cache,id=pnpm,target=/pnpm/store,sharing=locked \
    pnpm install --prod --frozen-lockfile --ignore-scripts --store-dir "${PNPM_STORE_DIR}" --config.confirmModulesPurge=false

FROM ${DOCKERHUB_REGISTRY}/library/node:24-alpine AS runtime

ARG NGINX_LISTEN_OPTS

ENV GDAL_LIBRARY_PATH="/usr/lib/libgdal.so" \
    GEOS_LIBRARY_PATH="/usr/lib/libgeos_c.so" \
    PATH="/seed/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /seed

# nginx must be >= 1.30.7: earlier releases have the HTTP/2 flaws CVE-2026-123633 and
# CVE-2026-123007 (remote code execution when http2 is enabled via NGINX_LISTEN_OPTS).
# The version floor also invalidates a cached layer that still holds an older nginx and
# makes the build fail instead of shipping a vulnerable package.
RUN apk add --no-cache \
        bash \
        brotli \
        coreutils \
        curl \
        gdal-dev \
        geos-dev \
        gettext \
        git \
        libbz2 \
        libffi \
        libxml2 \
        libxslt \
        ncurses-libs \
        'nginx>=1.30.7-r0' \
        'nginx-mod-http-brotli>=1.30.7-r0' \
        openssl \
        libpq \
        pcre \
        readline \
        sqlite-libs \
        tzdata \
        xz-libs \
        zlib && \
    mkdir -p /run/nginx /var/log/supervisord && \
    # Remove the npm CLI bundled with the base node image: this app installs all JS
    # dependencies via pnpm and never invokes npm/npx at build or run time, so dropping it
    # trims unused attack surface
    rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx

## Note on some of the commands above:
##   - coreutils is required due to an issue with our wait-for-it.sh script:
##     https://github.com/vishnubob/wait-for-it/issues/71

COPY --from=python-deps /opt/uv/python /opt/uv/python
COPY --from=python-deps /seed/.venv /seed/.venv
COPY --from=node-runtime-deps /seed/node_modules /seed/node_modules
COPY --from=node-runtime-deps /seed/vendors/node_modules /seed/vendors/node_modules

### Copy over the SEED application and prebuilt frontend assets
COPY ./backend /seed/
COPY ./docker /seed/docker
COPY ./LICENSE.md /seed/LICENSE.md
# The version endpoint reads the commit with `git rev-parse`; the wildcard keeps
# builds from contexts without .git (e.g., a Git URL) working
COPY ./.gi[t] /seed/.git
COPY --from=frontend-build /repo/backend/collected_static/ng-app /seed/collected_static/ng-app
COPY ./docker/wait-for-it.sh /usr/local/wait-for-it.sh
RUN git config --system --add safe.directory /seed

# nginx configuration - replace the root/default nginx config file and add included files
COPY ./docker/nginx/*.conf /etc/nginx/
COPY ./docker/nginx/nginx.conf.template /etc/nginx/nginx.conf.template

# Generate nginx.conf from the template (gettext/envsubst installed above).
RUN if [ -z "${NGINX_LISTEN_OPTS}" ]; then \
        echo "NGINX_LISTEN_OPTS is unset or empty, defaulting to: HTTP1.1"; \
    else \
        echo "NGINX_LISTEN_OPTS is set to: ${NGINX_LISTEN_OPTS}"; \
    fi && \
    envsubst '${NGINX_LISTEN_OPTS}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# symlink maintenance.html that nginx will serve in the case of a 503
RUN ln -sf /seed/collected_static/maintenance.html /var/lib/nginx/html/maintenance.html && \
    chmod +x ./docker/maintenance.sh

# Supervisor looks in /etc/supervisor for the configuration file.
COPY ./docker/supervisor-seed.conf /etc/supervisor/supervisord.conf

# entrypoint sets some permissions on directories that may be shared volumes
COPY ./docker/seed-entrypoint.sh /usr/local/bin/seed-entrypoint
RUN chmod 775 /usr/local/bin/seed-entrypoint
ENTRYPOINT ["seed-entrypoint"]

EXPOSE 80

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
