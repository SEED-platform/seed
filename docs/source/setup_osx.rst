Installation on macOS
=====================

These instructions are for running SEED locally on macOS for development.

SEED currently uses:

* Python 3.14 in ``.python-version``; ``pyproject.toml`` requires Python 3.12 or newer.
* ``uv`` for Python installation and dependency management.
* PostgreSQL with PostGIS. PostgreSQL 16 is a good local development target.
* Redis for cache. Basic local development only runs Celery tasks eagerly in
  the Django process.
* Node 24 and pnpm 11 for JavaScript dependencies.
* A separate Angular UI checked out as the ``ng_seed/seed-angular`` git submodule.

Quick Installation Instructions
-------------------------------

This section assumes Homebrew and git are already installed.

.. code-block:: bash

    brew install graphviz postgresql@16 postgis redis uv node@24
    corepack enable

    git clone git@github.com:SEED-platform/seed.git
    cd seed
    git submodule update --init ng_seed/seed-angular

    uv sync
    pnpm install

    cp config/settings/local_untracked.py.dist config/settings/local_untracked.py

Edit ``config/settings/local_untracked.py`` for your local database and Redis
settings. Then run:

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    uv run manage.py migrate
    uv run manage.py create_default_user --username=admin@my.org --organization=seedorg --password=badpass
    uv run manage.py runserver

Run Django management commands through ``uv`` as ``uv run manage.py <command>``.

The AngularJS application runs at http://127.0.0.1:8000/app/.

The new Angular application runs at http://127.0.0.1:8000/ng-app/ after its
static files have been built. For active Angular development, see
``ng_seed/README.md``.

PostgreSQL, PostGIS, and TimescaleDB
------------------------------------

Install and start PostgreSQL 16:

.. code-block:: bash

    brew install postgresql@16 postgis
    brew services start postgresql@16

Make sure the PostgreSQL 16 binaries are in your shell path. Homebrew prints
the exact path after installation; on Apple Silicon it is usually:

.. code-block:: bash

    export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

Create a local database and user. The development settings default to a
database named ``seed`` with user/password ``postgres``/``postgres``, but those
values can be changed in ``config/settings/local_untracked.py``.

.. code-block:: bash

    createuser -P postgres
    createdb -O postgres seed
    psql -d seed -c "CREATE EXTENSION IF NOT EXISTS postgis;"

Some SEED features use TimescaleDB. If you need those features locally, install
a TimescaleDB build compatible with your PostgreSQL version, add
``timescaledb`` to ``shared_preload_libraries`` in ``postgresql.conf``, restart
PostgreSQL, and enable the extension:

.. code-block:: bash

    psql -d seed -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

The Docker development environment uses the repository's configured
TimescaleDB/Postgres image instead, which is currently
``timescale/timescaledb-ha:pg18.3-ts2.26.4-oss``.

Using Docker Postgres and Redis with Local Django
-------------------------------------------------

If you want to run Django directly on macOS, but use the repository's Docker
services for Postgres and Redis, start only those services:

.. code-block:: bash

    docker compose up -d db-postgres db-redis

Make sure ``config/settings/local_untracked.py`` matches the Docker database
you intend to use. For example, if your local settings point at a database named
``seeddev1`` with user ``seed``, create that database in the running container
and enable PostGIS before running migrations:

.. code-block:: bash

    docker exec seed_postgres createdb -U seed -O seed seeddev1
    docker exec seed_postgres psql -U seed -d seeddev1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"

Then run the normal local setup commands:

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    uv run manage.py migrate
    uv run manage.py create_default_user
    uv run manage.py runserver

The default ``create_default_user`` credentials are ``demo@seed-platform.org``
with password ``demo`` in organization ``demo``. Pass ``--username``,
``--password``, and ``--organization`` if you want different local credentials.

Redis
-----

Install and start Redis:

.. code-block:: bash

    brew install redis
    brew services start redis

Configure ``config/settings/local_untracked.py`` to use local Redis:

.. code-block:: python

    CELERY_BROKER_URL = "redis://127.0.0.1:6379/1"
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": CELERY_BROKER_URL,
        }
    }
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

Python Dependencies
-------------------

Install Python dependencies from the lockfile:

.. code-block:: bash

    uv sync

``uv sync`` creates or updates the project virtual environment and installs the
default dependency groups from ``uv.lock``. The repository currently includes
the ``dev`` dependency group by default.

JavaScript Dependencies
-----------------------

The root project expects Node 24 or newer and pnpm 11 or newer. The Angular UI
submodule expects Node 22 or newer and pnpm 10 or newer, so Node 24/pnpm 11
satisfies both.

.. code-block:: bash

    corepack enable
    pnpm install

If the Angular submodule is not checked out, initialize it first:

.. code-block:: bash

    git submodule update --init ng_seed/seed-angular

To build the Angular UI for Django to serve at ``/ng-app/``:

.. code-block:: bash

    cd ng_seed/seed-angular
    pnpm build

For hot reloading during Angular UI development:

.. code-block:: bash

    cd ng_seed/seed-angular
    pnpm start

Then browse to http://localhost:4200.

Configure Django
----------------

Create your local settings file:

.. code-block:: bash

    cp config/settings/local_untracked.py.dist config/settings/local_untracked.py

At minimum, update the ``DATABASES``, ``CELERY_BROKER_URL``, ``CACHES``,
``CELERY_RESULT_BACKEND``, and eager Celery values. A typical local database
section is:

.. code-block:: python

    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": "seed",
            "USER": "postgres",
            "PASSWORD": "postgres",
            "HOST": "127.0.0.1",
            "PORT": "5432",
        }
    }

Run Migrations and Create a User
--------------------------------

Run Django management commands through ``uv`` as ``uv run manage.py <command>``.

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    uv run manage.py migrate
    uv run manage.py create_default_user --username=admin@my.org --organization=seedorg --password=badpass

Start SEED
----------

For basic local development only, run Celery tasks eagerly in the Django process
and start only Django:

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    uv run manage.py runserver

Open http://127.0.0.1:8000/app/ and log in with the user created above.

Running an Async Celery Worker
------------------------------

Testing workflows that need real asynchronous behavior and production-like
deployments should run Celery as a separate worker/task. For that mode, disable
eager execution in ``config/settings/local_untracked.py``:

.. code-block:: python

    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = False

Then start Celery in another terminal:

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    uv run celery -A seed worker -l INFO -c 4 --max-tasks-per-child 1000 -EBS django_celery_beat.schedulers:DatabaseScheduler

The health endpoint pings live Celery workers:

.. code-block:: bash

    curl -i http://127.0.0.1:8000/api/health_check/

With a worker running, a healthy local stack returns ``200 OK`` with
``postgres``, ``redis``, and ``celery`` all set to ``success``. In eager mode
without a worker, ``postgres`` and ``redis`` can still be ``success`` while
``celery`` is ``error``; that is expected for the basic local setup.

MapQuest API Key
----------------

Geocoding requires a MapQuest API key. Add the key to the target organization
from the organization's settings page, or set ``MAPQUEST_API_KEY`` in
``config/settings/local_untracked.py`` for local development.
