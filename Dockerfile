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
        enchant \
        python-numpy \
        python-scipy \
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

### link the apt install of nodejs to node (expected by bower)
RUN ln -s /usr/bin/nodejs /usr/bin/node

WORKDIR /seed
### Install JavaScript requirements - do this first because they take awhile
### and the dependencies will probably change slower than python packages.
### README.md stops the no readme warning
COPY ./bower.json /seed/bower.json
COPY ./.bowerrc /seed/.bowerrc
COPY ./package.json /seed/package.json
COPY ./README.md /seed/README.md
#RUN npm update
COPY ./bin/install_javascript_dependencies.sh /seed/bin/install_javascript_dependencies.sh
RUN /seed/bin/install_javascript_dependencies.sh

### Install python requirements
COPY ./requirements.txt /seed/requirements.txt
COPY ./requirements/*.txt /seed/requirements/
RUN pip install -r requirements/local.txt

### Copy over the remaining part of the SEED application
COPY . /seed/
COPY ./config/settings/local_untracked_docker.py /seed/config/settings/local_untracked.py

EXPOSE 8000
