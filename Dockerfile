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
    && ln -s /usr/bin/nodejs /usr/bin/node

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
RUN npm update
COPY ./bin/install_javascript_dependencies.sh /seed/bin/install_javascript_dependencies.sh
RUN /seed/bin/install_javascript_dependencies.sh

# Temp app for testing the ports
RUN apt-get update && apt-get install -y nmap

### Copy over the remaining part of the SEED application and some helpers
COPY . /seed/
COPY ./docker/wait-for-it.sh /usr/local/wait-for-it.sh

# configure nginx
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY /docker/nginx-seed.conf /etc/nginx/sites-available/default
COPY /docker/supervisor-seed.conf /etc/supervisor/conf.d/supervisor-seed.conf

# ENTRYPOINT handles compilation of assets
COPY /docker/seed-entrypoint.sh /usr/local/bin/seed-entrypoint
RUN chmod 775 /usr/local/bin/seed-entrypoint
ENTRYPOINT ["seed-entrypoint"]

#CMD ["/seed/docker/start_uwsgi_docker.sh"]
CMD ["supervisord", "-n"]

EXPOSE 80
EXPOSE 8000
EXPOSE 8001
