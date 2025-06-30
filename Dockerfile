ARG NGINX_LISTEN_OPTS

# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nrel.gov>
# DESCRIPTION:      Image with seed platform and dependencies running in development mode
# TO_BUILD_AND_RUN: docker compose build && docker compose up

FROM node:22-alpine3.19

ARG NGINX_LISTEN_OPTS

RUN apk add --no-cache \
        postgresql-dev \
        coreutils \
        alpine-sdk \
        pcre \
        pcre-dev \
        libxslt-dev \
        linux-headers \
        libffi-dev \
        bash \
        bash-completion \
        nginx \
        brotli \
        nginx-mod-http-brotli \
        openssl-dev \
        geos-dev \
        gdal \
        gdal-dev \
        gcc \
        musl-dev \
        cargo \
        tzdata \
        bzip2-dev \
        readline-dev \
        sqlite-dev \
        ncurses-dev \
        xz-dev \
        zlib-dev \
        libxml2-dev && \
    mkdir -p /var/log/supervisord && \
    mkdir -p /run/nginx

## Note on some of the commands above:
##   - coreutils is required due to an issue with our wait-for-it.sch script:
##     https://github.com/vishnubob/wait-for-it/issues/71

# Install pyenv and Python globally
ENV PYTHON_VERSION=3.9.22
ENV PYENV_ROOT="/opt/pyenv"
ENV PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"

RUN git clone https://github.com/pyenv/pyenv.git $PYENV_ROOT && \
    $PYENV_ROOT/bin/pyenv install $PYTHON_VERSION && \
    $PYENV_ROOT/bin/pyenv global $PYTHON_VERSION && \
    ln -sf $PYENV_ROOT/shims/python /usr/local/bin/python && \
    ln -sf $PYENV_ROOT/shims/python3 /usr/local/bin/python3 && \
    ln -sf $PYENV_ROOT/shims/pip /usr/local/bin/pip && \
    ln -sf $PYENV_ROOT/shims/pip3 /usr/local/bin/pip3

# Make sure non-root users inherit pyenv paths
ENV PYENV_ROOT="/opt/pyenv"
ENV PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"

# Install pip
RUN bash -c "python3 -m ensurepip --upgrade && python3 -m pip install --upgrade pip setuptools && \
    pip install supervisor==4.2.5"

### Install python requirements
WORKDIR /seed
COPY ./requirements.txt /seed/requirements.txt
COPY ./requirements/*.txt /seed/requirements/
RUN pip uninstall -y enum34
RUN pip install -r requirements/aws.txt

### Install JavaScript requirements - do this first because they take a while
### and the dependencies will probably change slower than python packages.
### README.md stops the no readme warning
COPY ./package.json /seed/package.json
COPY ./package-lock.json /seed/package-lock.json
COPY ./vendors/package.json /seed/vendors/package.json
COPY ./vendors/package-lock.json /seed/vendors/package-lock.json
COPY ./ng_seed/seed-angular/package.json /seed/ng_seed/seed-angular/package.json
COPY ./ng_seed/seed-angular/pnpm-lock.yaml /seed/ng_seed/seed-angular/pnpm-lock.yaml
COPY ./ng_seed/seed-angular/pnpm-workspace.yaml /seed/ng_seed/seed-angular/pnpm-workspace.yaml
COPY ./README.md /seed/README.md
# unsafe-perm allows the package.json postinstall script to run with the elevated permissions
RUN npm install -g pnpm
RUN npm install --omit=dev --unsafe-perm

### Copy over the remaining part of the SEED application and some helpers
WORKDIR /seed
COPY . /seed/
COPY ./docker/wait-for-it.sh /usr/local/wait-for-it.sh
RUN git config --system --add safe.directory /seed

### Build SEED Angular then cleanup
RUN pnpm -C /seed/ng_seed/seed-angular build
RUN rm -rf /seed/ng_seed/seed-angular/node_modules
RUN pnpm store prune

# nginx configuration - replace the root/default nginx config file and add included files
COPY ./docker/nginx/*.conf /etc/nginx/
COPY ./docker/nginx/nginx.conf.template /etc/nginx/nginx.conf.template

# Install gettext package for envsubst and then generate nginx.conf from the template
RUN apk add --no-cache gettext && \
    if [ -z "${NGINX_LISTEN_OPTS}" ]; then \
        echo "NGINX_LISTEN_OPTS is unset or empty, defaulting to: HTTP1.1"; \
    else \
        echo "NGINX_LISTEN_OPTS is set to: ${NGINX_LISTEN_OPTS}"; \
    fi && \
    envsubst '${NGINX_LISTEN_OPTS}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# symlink maintenance.html that nginx will serve in the case of a 503
RUN ln -sf /seed/collected_static/maintenance.html /var/lib/nginx/html/maintenance.html
# set execute permissions on the maint script to toggle on and off
RUN chmod +x ./docker/maintenance.sh

# Supervisor looks in /etc/supervisor for the configuration file.
COPY ./docker/supervisor-seed.conf /etc/supervisor/supervisord.conf

# entrypoint sets some permissions on directories that may be shared volumes
COPY ./docker/seed-entrypoint.sh /usr/local/bin/seed-entrypoint
RUN chmod 775 /usr/local/bin/seed-entrypoint
ENTRYPOINT ["seed-entrypoint"]

EXPOSE 80

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
