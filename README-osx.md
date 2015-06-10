# Development version of SEED on a Mac

These instructions are for installing and running SEED on Mac OSX in development mode.

## Prerequisites

These instructions assume you have/use [Macports](https://www.macports.org/). The workflow has been tested with homebrew as well, but is not directly supported. You system should have the following dependencies already installed:

* git (`port install git` or `brew install git`)
* Mercurial (`port install hg` or `brew install mercurial`)

(Recommended)

* [virtualenv](https://virtualenv.pypa.io/en/latest/) and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/).
    * Although you _could_ install Python packages globally, this is the easiest way to install Python packages. Setting these up first will help avoid polluting your base Python installation and make it much easier to switch between different versions of the code.

        pip install virtualenv
        pip install virtualenvwrapper

    * Follow instructions on [virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/) to setup your environment.
    * Once you have these installed, creating and entering a new virtualenv called "``seed``" for SEED development is as easy as:

        mkvirtualenv --python=python2.7 seed

## Install PostgreSQL 9.4

Perform the following commands as 'root' if using port

    sudo su - root
    
Install Postgres 9.4

    port install postgresql94-server postgresql94 postgresql94-doc
    # init db
    mkdir -p /opt/local/var/db/postgresql94/defaultdb
    chown postgres:postgres /opt/local/var/db/postgresql94/defaultdb

    # homebrew
    brew install postgres
    # follow the post install instructions to add to launchagents or call manually with `postgres -D /usr/local/var/postgres`
    # Skip the remaining Postgres instructions!

Finish initializing the DB

    sudo su postgres -c '/opt/local/lib/postgresql94/bin/initdb -D /opt/local/var/db/postgresql94/defaultdb'

At this point, you may want to add start/stop scripts or aliases to ~/.bashrc or your virtualenv ``postactivate`` script (in ``~/.virtualenvs/{env-name}/bin/postactivate``).

    alias pg_start='sudo su postgres -c "/opt/local/lib/postgresql94/bin/pg_ctl \
        -D /opt/local/var/db/postgresql94/defaultdb \
        -l /opt/local/var/db/postgresql94/defaultdb/postgresql.log start"'
    alias pg_stop='sudo su postgres -c "/opt/local/lib/postgresql94/bin/pg_ctl \
        -D /opt/local/var/db/postgresql94/defaultdb stop"'

Start Postgres

    pg_start
  
Switch to postgres user

    sudo su - postgres
    PATH=$PATH:/opt/local/lib/postgresql94/bin/
      
Configure PostgreSQL. Replace 'seeddb', 'seeduser' with desired db/user. By default use password `seedpass` when prompted

    createdb seeddb
    createuser -P seeduser
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seeddb" TO seeduser;'
    psql -c 'ALTER USER seeduser CREATEDB;'
    psql -c 'ALTER USER seeduser CREATEROLE;'

Now exit any root environments, becoming just yourself (even though it's not that easy being green..), for the remainder of these instructions.

## Install Python packages

Run these commands as your normal user id.

Change to a virtualenv (using virtualenvwrapper) or do the following as a superuser. A virtualenv is usually better for development. Set the virtualenv to seed.

    workon seed

Make sure PostgreSQL command line scripts are in your PATH (if using port)

    export PATH=$PATH:/opt/local/lib/postgresql94/bin

Some packages (uWSGI) may need to find your C compiler. Make sure you have 'gcc' on your system, and then also export this to the `CC` environment variable:

    export CC=gcc
    
Install requirements with `pip`

    pip install -r requirements.txt

    
Install library with `setup.py`

    python setup.py install
    
## Install Javascript libraries

### Install nodejs/npm

First, install [npm](https://www.npmjs.com/) if you haven't already. You can do this by installing from [nodejs.org](http://nodejs.org/), or use Macports:

    # port
    sudo port install npm

    # homebrew
    brew install npm

## Configure Django and its back-end DBs

In the `BE/settings` directory, there must be a file called `local_untracked.py` that sets up databases and a number of other things. To create and edit this file, start by copying over the template

    cd BE/settings
    cp local_untracked.py.dist local_untracked.py

### Edit `local_untracked.py`

Then open the file you created in your favorite editor.
Edit the postgresql config to look like this:

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

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "127.0.0.1:6379",
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }   
    BROKER_URL = 'redis://127.0.0.1:6379/1'

### Run Django migrations

Change back to the root of the repository. Now run the migration script to set up the database tables

    export DJANGO_SETTINGS_MODULE=BE.settings.dev
    ./manage.py syncdb --migrate
    
### Create Django admin user

You need a Django admin (super) user.

    ./manage.py create_default_user --username=admin@my.org --organization=lbnl --password=badpass
    
Of course, you need to save this user/password somewhere, since this is what you will use to login to the SEED website.

If you want to do any API testing (and of course you do!), you will
need to add an API KEY for this user.
You can do this in postgresql directly:

    psql seeddb seeduser
    seeddb=> update landing_seeduser set api_key='DEADBEEF' where id=1;

The 'secret' key DEADBEEF is hard-coded into the test scripts.

### Install Redis

You need to manually install Redis for Celery to work.

    # port
    sudo port install redis

    # homebrew
    brew install redis
    # follow the post install instructions to add to launchagents or call manually with `redis-server`

### Install Javascript dependencies

The JS dependencies are installed using node.js package management (npm), with
a helper package called `bower`. 

    ./bin/install_javascript_dependencies.sh

## Run the development server

You should put the following statement in ~/.bashrc or add it to the virtualenv post-activation script (e.g., in `~/.virtualenvs/seed/bin/postactivate`).

    export DJANGO_SETTINGS_MODULE=BE.settings.dev

The combination of Redis, Celery, and Django have been encapsulated in a 
single shell script, which examines existing processes and doesn't start
duplicate instances:

    ./bin/start-seed.sh
    
When this script is done, the Django stand-alone server will be running in 
the foreground.

### Login to the web page

Open your browser and navigate to [127.0.0.1:8000](http://127.0.0.1:8000) .

Login with the user/password you created before, e.g., `admin@my.org` and `badpass`.

Note that these steps have been combined into a script called `start-seed.sh`.
The script will also try to not start Celery or Redis if they already seem
to be running.
