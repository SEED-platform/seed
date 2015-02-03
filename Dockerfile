# VERSION 0.1
# AUTHOR:         Clay Teeter <teeterc@gmail.com>
# DESCRIPTION:    Image with seed platform and dependecies
# TO_BUILD:       docker build -rm -t seed-platform .
# TO_RUN_CELERY:  docker run -d -name seed-celery -v $HOME/seed_data:/seed/collected_static --link seed-redis:redis --link seed-postgres:postgres seed-platform /seed/bin/start_celery_docker.sh
# TO_RUN_UWSGI:  docker run -d -name seed-uwsgi -v $HOME/seed_data:/seed/collected_static --link seed-redis:redis --link seed-postgres:postgres -p 8000:8000 seed-platform /seed/bin/start_uwsgi_docker.sh

# Latest Ubuntu LTS
FROM ubuntu:14.04

# Update
RUN apt-get update \
    && apt-get install -y \
        emacs24-nox \
        swig \
        python-pip \
        python-dev \
        libssl-dev \
        liblzma-dev \
        libevent1-dev \
	git \
	mercurial \
        libpq-dev \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

### install python requirements
COPY ./requirements.txt /seed/requirements.txt

WORKDIR /seed
RUN pip install -r requirements.txt

### link the apt install of nodejs to node (expected by bower)
RUN ln -s /usr/bin/nodejs /usr/bin/node

COPY ./bower.json /seed/bower.json
COPY ./.bowerrc /seed/.bowerrc

RUN npm update && npm install -g bower && bower install --allow-root

WORKDIR /seed/seed/static/vendors/bower_components/fine-uploader
RUN npm install -g grunt-cli

### There is a depencency issue with fine-uploader 3.1.9.  Everything compiles fine in later versions.  
### Everything but karma installs, so grunt will still build the dist. 

RUN if npm install; then echo "installed"; else true; fi
RUN grunt package

COPY . /seed/

WORKDIR /root

EXPOSE 8000
