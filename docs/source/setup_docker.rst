.. todo:: These instructions are out of date and will be updated soon.

Installation on Docker
======================

.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/
.. _MacPorts: https://www.macports.org/
.. _Homebrew: http://brew.sh/
.. _npm: https://www.npmjs.com/
.. _nodejs.org: http://nodejs.org/
.. _Docker-Toolbox: https://docs.docker.com/toolbox/overview/
.. _Docker: https://docs.docker.com/installation/
.. _Docker-Machine: https://docs.docker.com/machine/install-machine/
.. _Docker-Compose: https://docs.docker.com/compose/install/
.. _Be Patient: https://www.youtube.com/watch?v=f4hkPn0Un_Q

Installing on Windows and OS X
===============================

Install Docker Toolbox (Windows/OS X)
-------------------------------------

Install Docker-Toolbox_, which installs several applications
including Docker, Docker Machine, and Docker Compose. It is possible to
install these individually as well by installing Docker_, Docker-Machine_,
and Docker-Compose_.

Create Docker-Machine Image
---------------------------

The command below will create a 100GB volume for development. This is a very large volume and can be adjusted. Make sure to create a volume greater than 30GB.

.. code-block:: bash

    docker-machine create --virtualbox-disk-size 100000 -d virtualbox dev


Start Docker-Machine Image
--------------------------

.. code-block:: bash

    docker-machine start dev  # if not already running
    eval $(docker-machine env dev)


Run Docker Compose
------------------

.. code-block:: bash

    docker-compose build

`Be Patient`_ ... If the containers build successfully, then start the containers

.. code-block:: bash

    docker-compose up

**Note that you may need to build the containers a couple times for everything to converge**

Create User
-----------

.. code-block:: bash

    docker-compose run web ./manage.py create_default_user


Login
-----

Get the Docker IP address (`docker-machine ip dev`) and point your browser
at [http://`ip-address`:8000](http://`ip-address`:8000) and log in with the
account:

.. code-block:: bash

    username: demo@seed.lbl.gov
    password: demo

Installing Docker on Ubuntu
============================

Docker will run directly on Ubuntu, so, in contrast to Windows/OS X there is no
need to run in in Virtual Box, unless desired. Running without Virtual Box means
you can set it up so that local changes are reflected in the containers and you
can edit files etc with your normal setup.

First follow the instructions here:
https://docs.docker.com/engine/installation/linux/ubuntulinux/

If you set up a docker group and add yourself to it you can run docker commands
directly. Otherwise you will need to precede docker commands with sudo. You will
need to log out entirely for the changes to take place. You can test this by
running

.. code-block:: bash

   docker run hello-world

if you still have issues, try rebooting.

If you ran the hello-word docker you can use the following to clean up.
First check to see what existing containers there are, and what there status is:

.. code-block:: bash

    docker ps -a

You should see something similar to this if there are no containers.

::
    CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS               NAMES

If you ran the hello world container you should see it listed (the image is
hello-word).Check its status to make sure it exited. Then you can go ahead and
remove it. A quick way to remove all old containers is this.

.. code-block:: bash

    docker rm $(docker ps -a -q)

Otherwise specify the numeric id to remove individual containers.

Next you can list images in a similar way.

.. code-block:: bash

    docker images

Images not connected to a container are known as dangling images. You can get
rid of them using this command:


.. code-block:: bash

    docker rmi -f $(docker images -q -a -f dangling=true)

Otherwise they can be removed using `docker rmi image` using the image name or id
shown by docker images.

Install Docker Compose
----------------------

.. code-block:: bash

    sudo apt-get install python-pip
    sudo pip install docker-compose

Optionally install Virtual Box and Docker-Machine
-------------------------------------------------

This is only necessary if you want to run inside Virtual Box.

.. code-block:: bash

    sudo apt-get install virtual-box
    wget https://github.com/docker/machine/releases/download/v0.7.0/docker-machine-`uname -s`-`uname -m`
    sudo mv docker-$(uname -s)-$(uname -m) /usr/local/bin/docker-machine
    sudo chmod +x /usr/local/bin/docker-machine

If you do this proceed by following the instructions for Windows/OS X starting
from Create Docker-Machine Image.

Setting up without a Virtual Machine
-------------------------------------

If we don't use Virtual Box we can run Docker directly. This assumes you are in
the same directory as the Git repo. You should also set up a virtualenv for it.
Setting it up  this way means it will use your local ip, so you will be able to
access the SEED website via localhost. As we are using containers we don't have to worry
about setting up the database and Redis directly, Docker will do this for us.

In this part we are going to set up the project so that the seed directory in
web container's root file system points to the copy on your local file system
(i.e. the directory with the repo in it). This is an advantage of running
docker directly: changes on your local file system show up in the container so
you can edit with your local tools etc. without having to have them running in
the container.

Before you start ensure you have set up a virtualenv for the project. Then at
a minimum you will need to install the tos module manually.

.. code-block:: bash

    pip install -e  'git+https://github.com/revsys/django-tos.git@aca823ccd12fdb897b2827832458b3c34e91dee6#egg=django_tos-master'

Note the quotes.

If you notice complaints about this not being present try:
`pip install ip install -r requirements/base.txt`, you might also need
to install test and local

Edit `docker-compose.yml` in the repo base.

Look for the section web:, then underneath it the volumes: section. Add two
lines like this:

`- $HOME/projects/seed:/seed`
`- $HOME/.virtualenvs/seed/src/django-tos-master:/seed/src/django-tos-master`


You will to change the part before the colon to match your local setup. On my
system the repo is a directory called seed under the projects folder in my home
directory for the first line. In the second line my virtualenvs live under
.virtualenvs  in my home directory as I use virtualenv wrapper. You will need
to adjust this to match your local setup.

Then you will need to open the ports for Redis and PostgreSQL. In the section
`db-postgres:` add

::
    ports:
        - "5432:5432"

in db-redis add

::
    ports:
        - "6379:6379"

You should be careful not to add the changes to this file to your git commits
as it is local only. You can do this with the following command.

.. code-block:: bash

    git update-index  --skip-worktree docker-compose.yml

Doing this ensures git preserves your local changes and will warn you of any
conflicts caused by upstream changes. Occasionally it might be necessary to
temporarily unset the flag using  `--no-skip-worktree` (you can reset it
afterwards). You can find more on how acts, and how to fix conflicts here:
http://fallengamer.livejournal.com/93321.html

Next do the following to create a local settings file

.. code-block:: bash

    cp config/settings/local_untracked.py.dist config/settings/local_untracked.py

Then you will need to edit the databases section. Here is a sample
::

    # postgres DB config
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'seed',
            'USER': 'seed',
            'PASSWORD': 'seed',
            'HOST': '172.17.0.1',
            'PORT': '5432',
        }
    }

The tricky part is the HOST line. The web server can't connect to the database on localhost
with this setup. Use `ifconfig` to find out the ip addresses on your
local machine. In this example 172.17.0.1 was listed for docker0 and that
worked.

Run Docker Compose
------------------

.. code-block:: bash

    docker-compose build

Note this process will spit out a warning that some containers are being ignored. Don't worry they will be set up later.

`Be Patient`_ ... If the containers build successfully, then start the containers

.. code-block:: bash

    docker-compose up

**Note that you may need to build the containers a couple times for everything to converge**. You will likely need to do this. Run `docker-compose up` hit Ctrl-C, then run both the commands again to get everything working correctly.

Note for whatever reason things like collectstatic aren't run automatically
if you aren't using Virtual Box. You can fix it with the following. Use this
to connect to a shell in the container.

.. code-block:: bash

    docker exec -it "seed_web_1" bash

Then run the following when you are there.

.. code-block:: bash

    bin/postcompile

You might see some errors, don't worry, these mostly occur because its trying
to use Amazon S3., which is not relevant here.

This should only need to be done once (unless things change, e.g. adding more static files) as long as the docker image is around.

Create User
-----------

.. code-block:: bash

    docker-compose run web ./manage.py create_default_user

Login
-----

Point your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000) and log in
with the account:

.. code-block:: bash

    username: demo@seed.lbl.gov
    password: demo
