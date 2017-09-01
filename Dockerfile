# VERSION 0.1
# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nrel.gov>
# DESCRIPTION:      Image with seed platform and dependencies running in development mode
# TO_BUILD_AND_RUN: docker-compose build && docker-compose up

# Latest Ubuntu LTS
FROM ubuntu:16.04

### Required dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        npm \
        nodejs \
        python2.7 \
        python-pip \
        python-dev \
        python-gdbm \
        libpcre3 \
        libpcre3-dev \
        nginx \
        supervisor \
        # dev dependencies
        enchant \
        vim \
        curl \
    && pip install --upgrade pip \
    && pip install setuptools \
    && groupadd --gid 1000 uwsgi \
    && useradd -g uwsgi -M -u 1000 -r uwsgi \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/nodejs /usr/bin/node \
    && echo "daemon off;" >> /etc/nginx/nginx.conf

# nginx configurations
COPY /docker/nginx-seed.conf /etc/nginx/sites-available/default
COPY /docker/supervisor-seed.conf /etc/supervisor/conf.d/supervisor-seed.conf

### Install python requirements
WORKDIR /seed
COPY ./requirements.txt /seed/requirements.txt
COPY ./requirements/*.txt /seed/requirements/
RUN pip install -r requirements/aws.txt


### Install JavaScript requirements - do this first because they take awhile
### and the dependencies will probably change slower than python packages.
### README.md stops the no readme warning
COPY ./bower.json /seed/bower.json
COPY ./.bowerrc /seed/.bowerrc
COPY ./package.json /seed/package.json
COPY ./README.md /seed/README.md
COPY ./bin/install_javascript_dependencies.sh /seed/bin/install_javascript_dependencies.sh
RUN npm update && /seed/bin/install_javascript_dependencies.sh

### Copy over the remaining part of the SEED application and some helpers
COPY . /seed/
COPY ./docker/wait-for-it.sh /usr/local/wait-for-it.sh

# collect the static assets and compress them. Commented out for now because it takes forever in
# in docker
#RUN ./manage.py collectstatic --no-input && ./manage.py compress --force

# entrypoint sets some permissions on directories that may be shared volumes
COPY /docker/seed-entrypoint.sh /usr/local/bin/seed-entrypoint
RUN chmod 775 /usr/local/bin/seed-entrypoint
ENTRYPOINT ["seed-entrypoint"]

CMD ["supervisord", "-n"]

EXPOSE 80
