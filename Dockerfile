# VERSION 0.1
# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nrel.gov>
# DESCRIPTION:      Image with seed platform and dependencies running in development mode
# TO_BUILD_AND_RUN: docker-compose build && docker-compose up

FROM alpine:3.8

RUN apk add --no-cache python \
        python3-dev \
        postgresql-dev \
        alpine-sdk \
        pcre \
        pcre-dev \
        libxslt-dev \
        linux-headers \
        libffi-dev \
        bash \
        bash-completion \
        npm \
        nginx && \
    apk add --no-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/main openssl && \
    apk add --no-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ geos gdal && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    python -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    pip install --upgrade pip setuptools && \
    pip install git+https://github.com/Supervisor/supervisor@837c159ae51f3 && \
    mkdir -p /var/log/supervisord/ && \
    rm -r /root/.cache && \
    addgroup -g 1000 uwsgi && \
    adduser -G uwsgi -H -u 1000 -S uwsgi && \
    mkdir -p /run/nginx && \
    echo "daemon off;" >> /etc/nginx/nginx.conf && \
    rm -f /etc/nginx/conf.d/default.conf

## Note on some of the commands above:
##   - create the uwsgi user and group to have id of 1000
##   - copy over python3 as python
##   - pip install --upgrade pip overwrites the pip so it is no longer a symlink
##   - install supervisor that works with Python3.
##   - enchant, python-gdbm, libssl-dev, libxml2-dev are no longer explicitly installed

### Install python requirements
WORKDIR /seed
COPY ./requirements.txt /seed/requirements.txt
COPY ./requirements/*.txt /seed/requirements/
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

# nginx configurations - alpine doesn't use the sites-available directory. Put seed
# configuration file into the /etc/nginx/conf.d/ folder.
COPY /docker/nginx-seed.conf /etc/nginx/conf.d/seed.conf

# Supervisor looks in /etc/supervisor for the configuration file.
COPY /docker/supervisor-seed.conf /etc/supervisor/supervisord.conf

# entrypoint sets some permissions on directories that may be shared volumes
COPY /docker/seed-entrypoint.sh /usr/local/bin/seed-entrypoint
RUN chmod 775 /usr/local/bin/seed-entrypoint
ENTRYPOINT ["seed-entrypoint"]

CMD ["supervisord"]

EXPOSE 80
