# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nrel.gov>
# DESCRIPTION:      Image with seed platform and dependencies running in development mode
# TO_BUILD_AND_RUN: docker-compose build && docker-compose up

FROM alpine:3.14

RUN apk add --no-cache python3-dev \
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
        npm \
        nginx \
        openssl-dev \
        geos \
        gdal \
        gcc \
        musl-dev \
        cargo && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    python -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    pip install --upgrade pip setuptools && \
    pip install supervisor==4.2.2 && \
    mkdir -p /var/log/supervisord/ && \
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

# nginx configuration - replace the root/default nginx config file
COPY /docker/nginx-seed.conf /etc/nginx/nginx.conf
# symlink maintenance.html that nginx will serve in the case of a 503
RUN ln -sf /seed/collected_static/maintenance.html /var/lib/nginx/html/maintenance.html
# set execute permissions on the maint script to toggle on and off
RUN chmod +x ./docker/maintenance.sh

# Supervisor looks in /etc/supervisor for the configuration file.
COPY /docker/supervisor-seed.conf /etc/supervisor/supervisord.conf

# entrypoint sets some permissions on directories that may be shared volumes
COPY /docker/seed-entrypoint.sh /usr/local/bin/seed-entrypoint
RUN chmod 775 /usr/local/bin/seed-entrypoint
ENTRYPOINT ["seed-entrypoint"]

CMD ["supervisord"]

EXPOSE 80
