ARG NGINX_LISTEN_OPTS

# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nrel.gov>
# DESCRIPTION:      Image with seed platform and dependencies running in development mode
# TO_BUILD_AND_RUN: docker compose build && docker compose up

FROM node:20-alpine AS node

FROM alpine:3.14

ARG NGINX_LISTEN_OPTS

COPY --from=node /usr/lib /usr/lib
COPY --from=node /usr/local/lib /usr/local/lib
COPY --from=node /usr/local/include /usr/local/include
COPY --from=node /usr/local/bin /usr/local/bin

RUN apk add --no-cache \
        python3-dev \
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
        openssl-dev \
        geos-dev \
        gdal \
        gcc \
        musl-dev \
        cargo \
        tzdata && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    python -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    pip install --upgrade pip setuptools && \
    pip install supervisor==4.2.5 && \
    mkdir -p /var/log/supervisord && \
    rm -r /root/.cache && \
    addgroup -g 1000 uwsgi && \
    adduser -G uwsgi -H -u 1000 -S uwsgi && \
    mkdir -p /run/nginx

## Note on some of the commands above:
##   - create the uwsgi user and group to have id of 1000
##   - copy over python3 as python
##   - pip install --upgrade pip overwrites the pip so it is no longer a symlink
##   - coreutils is required due to an issue with our wait-for-it.sch script:
##     https://github.com/vishnubob/wait-for-it/issues/71

### Install python requirements
WORKDIR /seed
COPY ./requirements.txt /seed/requirements.txt
COPY ./requirements/*.txt /seed/requirements/
RUN pip uninstall -y enum34
RUN pip install -r requirements/aws.txt

### Install JavaScript requirements - do this first because they take awhile
### and the dependencies will probably change slower than python packages.
### README.md stops the no readme warning
COPY ./package.json /seed/package.json
COPY ./vendors/package.json /seed/vendors/package.json
COPY ./README.md /seed/README.md
# unsafe-perm allows the package.json postinstall script to run with the elevated permissions
RUN npm install --unsafe-perm

### Copy over the remaining part of the SEED application and some helpers
WORKDIR /seed
COPY . /seed/
COPY ./docker/wait-for-it.sh /usr/local/wait-for-it.sh
RUN git config --system --add safe.directory /seed

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

CMD ["supervisord"]
