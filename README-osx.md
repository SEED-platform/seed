# Development version of SEED on a Mac

These instructions are for installing and running SEED on Mac OSX in development mode.

## Prerequisites

These instructions assume you have/use [Macports](https://www.macports.org/).

Although you _could_ install Python packages globally, the easiest way to install Python packages is with [virtualenv](https://virtualenv.pypa.io/en/latest/) and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/). Setting these up first will help avoid polluting your base Python installation and make it much easier to switch between different versions of the code.

Once you have these installed, creating and entering a new virtualenv called "``seed``" for SEED development is as easy as:

    mkvirtualenv --python=python2.7 seed
    

## Install PostgreSQL 9.4

Perform the following commands as 'root'

    sudo su - root
    
Install Postgres 9.4

    port install postgresql94-server postgresql94 postgresql94-doc
    # init db
    mkdir -p /opt/local/var/db/postgresql94/defaultdb
    chown postgres:postgres /opt/local/var/db/postgresql94/defaultdb
    
Finish initializing the DB

    sudo su postgres - c '/opt/local/lib/postgresql94/bin/initdb -D /opt/local/var/db/postgresql94/defaultdb'

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
      
Configure Postgresql. Replace 'seeddb', 'seeduser' with desired db/user.
seedpass

    createdb seeddb
    createuser -P seeduser
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seeddb" TO seeduser;'

Now exit any root environments, becoming just yourself (even though it's not that easy being green..), for the remainder of these instructions.

## Install Python packages

Run these commands as your normal user id.

Change to a virtualenv (using virtualenvwrapper) or do the following as a superuser. A virtualenv is usually better for development.

Make sure PostgreSQL command line scripts are in your PATH

    export PATH=$PATH:/opt/local/lib/postgresql94/bin
    
Install requirements with `pip`

    pip install -r requirements.txt
    
Install library with `setup.py`

    python setup.py install
    
## Install Javascript libraries

### Install nodejs/npm

First, install [npm](https://www.npmjs.com/) if you haven't already. You can do this by installing from [nodejs.org](http://nodejs.org/), or use Macports:

    sudo port install npm

### Install libraries

Then run, from the top-level, a script to install the JS libraries:

    ./bin/install_javascript_dependencies.sh

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

    psql94 seeddb seeduser
    seeddb=> update landing_seeduser set api_key='DEADBEEF' where id=1;

The 'secret' key DEADBEEF is hard-coded into the test scripts.

### Install Redis

You need to manually install Redis for Celery to work.

    sudo port install redis

## Run the development server

You should put the following statement in ~/.bashrc or add it to the virtualenv post-activation script (e.g., in `~/.virtualenvs/seed/bin/postactivate`).

    export DJANGO_SETTINGS_MODULE=BE.settings.dev

If you haven't already, you need to start the Redis server. For development, it is convenient to run it as yourself, logging to /tmp

    # run in background
    redis-server >/tmp/redis-server.log 2>&1 &

Next start Celery, also in the background and logging to /tmp

    ./manage.py celery worker -B -c 2 --loglevel=INFO -E --maxtasksperchild=1000 >/tmp/celery.log 2>&1 &
    
Finally, run the Django standalone server

    ./manage.py runserver --settings=BE.settings.dev
    
Login with the user/password you created before, e.g., `admin@my.org` and `badpass`.

Note that these steps have been combined into a script called `start-seed.sh`.
The script will also try to not start Celery or Redis if they already seem
to be running.