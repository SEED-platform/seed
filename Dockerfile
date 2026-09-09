# syntax=docker/dockerfile:1.7

ARG NGINX_LISTEN_OPTS
ARG UV_VERSION=0.11.9

# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nlr.gov>
# DESCRIPTION:      Production image with SEED Platform and runtime dependencies
# TO_BUILD_AND_RUN: docker compose build && docker compose up

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM node:24-alpine AS build-base
COPY --from=uv /uv /uvx /bin/

WORKDIR /seed

COPY ./.python-version /seed/.python-version

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
        curl \
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

COPY ./pyproject.toml /seed/pyproject.toml
COPY ./uv.lock /seed/uv.lock
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --managed-python --no-dev --no-install-project && \
    uv pip install supervisor==4.3.0

FROM build-base AS frontend-build
ENV CI=true

COPY ./package.json /seed/package.json
COPY ./pnpm-lock.yaml /seed/pnpm-lock.yaml
COPY ./pnpm-workspace.yaml /seed/pnpm-workspace.yaml
COPY ./vendors/package.json /seed/vendors/package.json
COPY ./vendors/pnpm-lock.yaml /seed/vendors/pnpm-lock.yaml
COPY ./ng_seed/seed-angular /seed/ng_seed/seed-angular
RUN --mount=type=cache,id=pnpm,target=/pnpm/store,sharing=locked \
    pnpm install --frozen-lockfile --store-dir "${PNPM_STORE_DIR}" --config.confirmModulesPurge=false && \
    cd /seed/ng_seed/seed-angular && \
    ./node_modules/.bin/ng build

FROM build-base AS node-runtime-deps
ENV CI=true

COPY ./package.json /seed/package.json
COPY ./pnpm-lock.yaml /seed/pnpm-lock.yaml
COPY ./pnpm-workspace.yaml /seed/pnpm-workspace.yaml
COPY ./vendors/package.json /seed/vendors/package.json
COPY ./vendors/pnpm-lock.yaml /seed/vendors/pnpm-lock.yaml
COPY ./ng_seed/seed-angular/package.json /seed/ng_seed/seed-angular/package.json
COPY ./ng_seed/seed-angular/pnpm-lock.yaml /seed/ng_seed/seed-angular/pnpm-lock.yaml
COPY ./ng_seed/seed-angular/pnpm-workspace.yaml /seed/ng_seed/seed-angular/pnpm-workspace.yaml
RUN --mount=type=cache,id=pnpm,target=/pnpm/store,sharing=locked \
    pnpm install --prod --frozen-lockfile --ignore-scripts --store-dir "${PNPM_STORE_DIR}" --config.confirmModulesPurge=false && \
    rm -rf /seed/ng_seed/seed-angular/node_modules

FROM node:24-alpine AS runtime

ARG NGINX_LISTEN_OPTS

ENV GDAL_LIBRARY_PATH="/usr/lib/libgdal.so" \
    GEOS_LIBRARY_PATH="/usr/lib/libgeos_c.so" \
    PATH="/seed/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /seed

RUN apk add --no-cache \
        bash \
        brotli \
        coreutils \
        gdal-dev \
        geos-dev \
        gettext \
        git \
        libbz2 \
        libffi \
        libxml2 \
        libxslt \
        ncurses-libs \
        nginx \
        nginx-mod-http-brotli \
        openssl \
        libpq \
        pcre \
        readline \
        sqlite-libs \
        tzdata \
        xz-libs \
        zlib && \
    mkdir -p /run/nginx /var/log/supervisord

## Note on some of the commands above:
##   - coreutils is required due to an issue with our wait-for-it.sh script:
##     https://github.com/vishnubob/wait-for-it/issues/71

COPY --from=python-deps /opt/uv/python /opt/uv/python
COPY --from=python-deps /seed/.venv /seed/.venv
COPY --from=node-runtime-deps /seed/node_modules /seed/node_modules
COPY --from=node-runtime-deps /seed/vendors/node_modules /seed/vendors/node_modules

### Copy over the SEED application and prebuilt frontend assets
COPY . /seed/
COPY --from=frontend-build /seed/collected_static/ng-app /seed/collected_static/ng-app
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
