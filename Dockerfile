# VERSION 0.1
# AUTHOR:           Clay Teeter <teeterc@gmail.com>, Nicholas Long <nicholas.long@nrel.gov>
# DESCRIPTION:      Image with seed platform and dependencies running in development mode
# TO_BUILD_AND_RUN: docker-compose build && docker-compose up

# Latest Ubuntu LTS
FROM ubuntu:16.10

### Required dependencies
RUN apt-get update && apt-get install -y --no-install-recommends npm \
        nodejs \
        build-essential \
        git \
        python2.7 \
        python-pip \
        python-dev \
        python-gdbm \
        libpcre3 \
        libpcre3-dev \
    && pip install --upgrade pip \
    && pip install setuptools \
    && rm -rf /var/lib/apt/lists/*

### Development Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends enchant \
        vim \
    && rm -rf /var/lib/apt/lists/*

##        emacs24-nox \
##        swig \
##        libssl-dev \
##        liblzma-dev \
##        libevent1-dev \
##        mercurial \
##        libpq-dev \
##        enchant \

### link the apt install of nodejs to node (expected by bower)
RUN ln -s /usr/bin/nodejs /usr/bin/node

### Install python requirements
WORKDIR /seed
COPY ./requirements.txt /seed/requirements.txt
COPY ./requirements/*.txt /seed/requirements/
RUN pip install -r requirements/local.txt

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

### Copy over the remaining part of the SEED application and some helpers
COPY . /seed/
COPY ./docker/wait-for-it.sh /usr/local/wait-for-it.sh
COPY ./config/settings/local_untracked_docker.py /seed/config/settings/local_untracked.py

EXPOSE 8000
