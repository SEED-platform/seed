Local Development on macOS and Windows
======================================

These instructions are for running SEED locally for development while using
Docker containers for PostgreSQL/PostGIS/TimescaleDB and Redis.

SEED currently uses:

* Python 3.14 in ``backend/.python-version``; ``backend/pyproject.toml`` requires Python 3.12 or newer.
* ``uv`` for Python installation and dependency management.
* Docker Compose services for PostgreSQL/PostGIS/TimescaleDB and Redis.
* Node 24 and pnpm 12 for JavaScript dependencies.

The Django project (including the legacy AngularJS UI) lives in ``backend/`` and
the Angular UI in ``frontend/``. Run Django, ``uv``, and backend ``pnpm``
commands from ``backend/``, and Docker Compose commands from the repository root.

Quick Installation Instructions
-------------------------------

macOS developers can use Homebrew for application tooling. PostgreSQL,
PostGIS, TimescaleDB, and Redis should run in Docker, not through Homebrew.

.. code-block:: bash

    brew install graphviz uv node@24
    corepack enable

Windows developers should use Docker Desktop with the WSL 2 backend enabled.
Run the repository commands from a WSL 2 shell. Do not install native Windows
PostgreSQL, PostGIS, TimescaleDB, or Redis for SEED development.

Clone the repository and install dependencies:

.. code-block:: bash

    git clone git@github.com:SEED-platform/seed.git
    cd seed/backend

    uv sync
    pnpm install
    pnpm --dir ../frontend install

    cp config/settings/local_untracked.py.dist config/settings/local_untracked.py

Start the Docker database and Redis services from the repository root:

.. code-block:: bash

    docker volume create --name=seed_pgdata
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db-postgres db-redis

Edit ``config/settings/local_untracked.py`` to point at those services. Then run:

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    uv run manage.py migrate
    uv run manage.py create_default_user --username=admin@my.org --organization=seedorg --password=badpass
    uv run manage.py runserver

Run Django management commands through ``uv`` as ``uv run manage.py <command>``.

The AngularJS application runs at http://127.0.0.1:8000/app/.

To see the new Angular application at http://127.0.0.1:8000/ng-app/, build its
static files and run the Django server. For active Angular development, see
``frontend/README.md``.

Docker Postgres and Redis with Local Django
-------------------------------------------

When running Django directly on the host, use the repository's Docker services
for Postgres and Redis:

.. code-block:: bash

    docker volume create --name=seed_pgdata
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db-postgres db-redis

The Compose database service uses the repository's configured
TimescaleDB/Postgres image, currently
``timescale/timescaledb-ha:pg18.3-ts2.26.4-oss``. It creates the default
database from the Compose environment:

* database: ``seed``
* user: ``seed``
* password: ``super-secret-password``
* host from local Django: ``127.0.0.1``
* port from local Django: ``5432``

The dev Compose override publishes Redis on ``127.0.0.1:6379`` for local
Django.

If you need to recreate the database from scratch, stop the services and remove
the development volume:

.. code-block:: bash

    docker compose -f docker-compose.yml -f docker-compose.dev.yml down
    docker volume rm seed_pgdata
    docker volume create --name=seed_pgdata
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db-postgres db-redis

Then run the normal local setup commands:

.. code-block:: bash

    export DJANGO_SETTINGS_MODULE=config.settings.dev
    uv run manage.py migrate
    uv run manage.py create_default_user
    uv run manage.py runserver

The default ``create_default_user`` credentials are ``demo@seed-platform.org``
with password ``demo`` in organization ``demo``. Pass ``--username``,
``--password``, and ``--organization`` if you want different local credentials.

Configure ``config/settings/local_untracked.py`` to use Docker Redis:

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

``backend/`` and ``frontend/`` are separate pnpm projects. Both expect Node 24
or newer and pnpm 12 or newer, and each pins its exact pnpm version in its
``package.json``.

.. code-block:: bash

    corepack enable
    pnpm install
    pnpm --dir ../frontend install

To build the Angular UI for Django to serve at ``/ng-app/`` (the build is
written to ``backend/collected_static/ng-app``):

.. code-block:: bash

    cd ../frontend
    pnpm build

Use ``pnpm watch`` instead to rebuild on every change. For hot reloading during
Angular UI development:

.. code-block:: bash

    cd ../frontend
    pnpm start

Then browse to http://localhost:4200.

Configure Django
----------------

Create your local settings file:

.. code-block:: bash

    cp config/settings/local_untracked.py.dist config/settings/local_untracked.py

At minimum, update the ``DATABASES``, ``CELERY_BROKER_URL``, ``CACHES``,
``CELERY_RESULT_BACKEND``, and eager Celery values. A typical local database
section that points at the Docker database container is:

.. code-block:: python

    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": "seed",
            "USER": "seed",
            "PASSWORD": "super-secret-password",
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
