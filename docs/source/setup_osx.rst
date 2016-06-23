Installation on OSX
===================

.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/
.. _MacPorts: https://www.macports.org/
.. _Homebrew: http://brew.sh/
.. _npm: https://www.npmjs.com/
.. _nodejs.org: http://nodejs.org/

These instructions are for installing and running SEED on Mac OSX in
development mode.

Quick Installation Instructions
-------------------------------

This section is intended for developers who may already have their machine
ready for general development. If this is not the case, skip to Prerequisites.

* install Postgres 9.4 and redis for cache and message broker
* use a virtualenv (if desired)
* `git clone git@github.com:seed-platform/seed.git`
* create a `local_untracked.py` in the `config/settings` folder and add CACHE and DB config (example `local_untracked.py.dist`)
* `export DJANGO_SETTINGS_MODULE=config.settings.dev`
* `pip install -r requirements/local.txt`
* `./manage.py syncdb`
* `./manage.py migrate`
* `./manage.py create_default_user`
* `./manage.py runserver`
* `celery -A seed worker -l info -c 4 --maxtasksperchild 1000 --events`
* navigate to `http://127.0.0.1:8000/app/#/profile/admin` in your browser to add users to organizations
* main app runs at `127.0.0.1:8000/app`

The `python manage.py create_default_user` will setup a default `superuser`
which must be used to access the system the first time. The management command
can also create other superusers.

.. code-block:: console

    ./manage.py create_default_user --username=demo@seed.lbl.gov --organization=lbl --password=demo123


Prerequisites
-------------

These instructions assume you have MacPorts_ or Homebrew_. Your system
should have the following dependencies already installed:

* git (`port install git` or `brew install git`)
* Mercurial (`port install hg` or `brew install mercurial`)
* graphviz (`brew install graphviz`)
* virtualenv_ and virtualenvwrapper_ (Recommended)

    .. note::

        Although you *could* install Python packages globally, this is the
        easiest way to install Python packages. Setting these up first will
        help avoid polluting your base Python installation and make it much
        easier to switch between different versions of the code.

    .. code-block:: bash

        pip install virtualenv
        pip install virtualenvwrapper

* Follow instructions on virtualenvwrapper_ to setup your environment.
* Once you have these installed, creating and entering a new virtualenv called "``seed``" for SEED development is by calling:

    .. code-block:: bash

        mkvirtualenv --python=python2.7 seed

PostgreSQL 9.4
--------------

MacPorts::

    sudo su - root
    port install postgresql94-server postgresql94 postgresql94-doc
    # init db
    mkdir -p /opt/local/var/db/postgresql94/defaultdb
    chown postgres:postgres /opt/local/var/db/postgresql94/defaultdb
    su postgres -c '/opt/local/lib/postgresql94/bin/initdb -D /opt/local/var/db/postgresql94/defaultdb'

    # At this point, you may want to add start/stop scripts or aliases to
    # ~/.bashrc or your virtualenv ``postactivate`` script
    # (in ``~/.virtualenvs/{env-name}/bin/postactivate``).

    alias pg_start='sudo su postgres -c "/opt/local/lib/postgresql94/bin/pg_ctl \
        -D /opt/local/var/db/postgresql94/defaultdb \
        -l /opt/local/var/db/postgresql94/defaultdb/postgresql.log start"'
    alias pg_stop='sudo su postgres -c "/opt/local/lib/postgresql94/bin/pg_ctl \
        -D /opt/local/var/db/postgresql94/defaultdb stop"'

    pg_start

    sudo su - postgres
    PATH=$PATH:/opt/local/lib/postgresql94/bin/

Homebrew::

    brew install postgres
    # follow the post install instructions to add to launchagents or call
    # manually with `postgres -D /usr/local/var/postgres`
    # Skip the remaining Postgres instructions!



Configure PostgreSQL. Replace 'seeddb', 'seeduser' with desired db/user. By
default use password `seedpass` when prompted

.. code-block:: bash

    createuser -P seeduser
    createdb `whoami`
    psql -c 'CREATE DATABASE "seeddb" WITH OWNER = "seeduser";'
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seeddb" TO seeduser;'
    psql -c 'ALTER USER seeduser CREATEDB;'
    psql -c 'ALTER USER seeduser CREATEROLE;'

Now exit any root environments, becoming just yourself (even though it's not
that easy being green), for the remainder of these instructions.

Python Packages
---------------

Run these commands as your normal user id.

Change to a virtualenv (using virtualenvwrapper) or do the following as a
superuser. A virtualenv is usually better for development. Set the virtualenv
to seed.

.. code-block:: bash

    workon seed

Make sure PostgreSQL command line scripts are in your PATH (if using port)

.. code-block:: bash

    export PATH=$PATH:/opt/local/lib/postgresql94/bin

Some packages (uWSGI) may need to find your C compiler. Make sure you have
'gcc' on your system, and then also export this to the `CC` environment
variable:

.. code-block:: bash

    export CC=gcc

Install requirements with `pip`

.. code-block:: bash

    pip install -r requirements/local.txt

Install library with `setup.py`

.. code-block:: bash

    python setup.py install

NodeJS/npm
----------

Install npm_. You can do this by installing from nodejs.org_, MacPorts, or
Homebrew:

MacPorts::

    sudo port install npm

Homebrew::

    brew install npm

Configure Django and Databases
------------------------------

In the `config/settings` directory, there must be a file called
`local_untracked.py` that sets up databases and a number of other things.
To create and edit this file, start by copying over the template

.. code-block:: bash

    cd config/settings
    cp local_untracked.py.dist local_untracked.py

Edit `local_untracked.py`. Open the file you created in your favorite editor. The PostgreSQL config section will look something like this:

.. code-block:: python

    # postgres DB config
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'seeddb',
            'USER': 'seeduser',
            'PASSWORD': 'seedpass',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

You may want to comment out the AWS settings.

For Redis, edit the `CACHES` and `BROKER_URL` values to look like this:

.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "127.0.0.1:6379",
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }
    BROKER_URL = 'redis://127.0.0.1:6379/1'

Run Django Migrations
---------------------

Change back to the root of the repository. Now run the migration script to set
up the database tables

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    ./manage.py migrate

Django Admin User
-----------------

You need a Django admin (super) user.

.. code-block:: bash

    ./manage.py create_default_user --username=admin@my.org --organization=lbnl --password=badpass

Of course, you need to save this user/password somewhere, since this is what
you will use to login to the SEED website.

If you want to do any API testing (and of course you do!), you will need to
add an API KEY for this user. You can do this in postgresql directly:

.. code-block:: bash

    psql seeddb seeduser
    seeddb=> update landing_seeduser set api_key='DEADBEEF' where id=1;

The 'secret' key DEADBEEF is hard-coded into the test scripts.

Install Redis
-------------

You need to manually install Redis for Celery to work.

MacPorts::

    sudo port install redis

Homebrew::

    brew install redis
    # follow the post install instructions to add to launchagents or
    # call manually with `redis-server`

Install JavaScript Dependencies
-------------------------------

The JS dependencies are installed using node.js package management (npm), with
a helper package called `bower`.

.. code-block:: bash

    ./bin/install_javascript_dependencies.sh

Start the Server
----------------

You should put the following statement in ~/.bashrc or add it to the
virtualenv post-activation script (e.g., in
`~/.virtualenvs/seed/bin/postactivate`).

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev

The combination of Redis, Celery, and Django have been encapsulated in a
single shell script, which examines existing processes and doesn't start
duplicate instances:

.. code-block:: bash

    ./bin/start-seed.sh

When this script is done, the Django stand-alone server will be running in
the foreground.

Login
-----

Open your browser and navigate to http://127.0.0.1:8000

Login with the user/password you created before, e.g., `admin@my.org` and
`badpass`.

.. note::

    these steps have been combined into a script called `start-seed.sh`.
    The script will also try to not start Celery or Redis if they already seem
    to be running.
    
