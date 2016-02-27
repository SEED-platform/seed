# VERSION 0.1
# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nrel.gov>
# DESCRIPTION:      Image with seed platform and dependencies running in production mode
# TO_BUILD_AND_RUN: docker-compose up

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
        libpcre3 \
        libpcre3-dev \
    && rm -rf /var/lib/apt/lists/*

### install python requirements
COPY ./requirements.txt /seed/requirements.txt
COPY ./requirements/*.txt /seed/requirements/

WORKDIR /seed
RUN pip install -r requirements/local.txt

### link the apt install of nodejs to node (expected by bower)
RUN ln -s /usr/bin/nodejs /usr/bin/node

COPY ./bower.json /seed/bower.json
COPY ./.bowerrc /seed/.bowerrc

RUN npm update && npm install -g bower && bower install --allow-root

WORKDIR /seed/seed/static/vendors/bower_components/fine-uploader
RUN npm install -g grunt-cli

### There is a dependency issue with fine-uploader 3.1.9.  Everything compiles fine in later versions.
### Everything but karma installs, so grunt will still build the dist. 

RUN if npm install; then echo "installed"; else true; fi
RUN grunt package

COPY . /seed/
COPY ./config/settings/local_untracked_docker.py /seed/config/settings/local_untracked.py

WORKDIR /seed

EXPOSE 8000
