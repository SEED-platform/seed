Installation using Docker
=========================

Docker works natively on Linux, macOS, and Windows through Docker Engine or
Docker Desktop. These instructions assume Docker Compose v2, which is invoked
as ``docker compose``.

Docker Compose starts the required PostgreSQL/PostGIS/TimescaleDB and Redis
containers. Developers do not need to install PostgreSQL, PostGIS, TimescaleDB,
or Redis on the host machine.

Before building, initialize the Angular UI submodule:

.. code-block:: bash

    git submodule update --init ng_seed/seed-angular

The Dockerfiles install Python with ``uv`` and use Node 24 with pnpm through
Corepack. The development image also builds the Angular UI assets that Django
serves from ``/ng-app/``.

Docker Native (Ubuntu)
----------------------

Follow instructions `here <https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`_.

* `Install Docker Compose <https://docs.docker.com/compose/install/>`_ if your
  Docker installation does not already include Compose v2.


Docker Native (Windows/macOS)
-----------------------------

Follow instructions `for Mac <https://docs.docker.com/docker-for-mac/install/>`_
or `for Windows <https://docs.docker.com/docker-for-windows/install/>`_.
Docker Desktop includes Compose v2.

On Windows, use Docker Desktop with the WSL 2 backend. Run repository commands
from a WSL 2 shell when you need Linux-compatible paths or shell behavior.


Building and Running Containers for Non-Development
-------------------------------------------------------

The Docker Compose database service uses ``timescale/timescaledb-ha:pg18.3-ts2.26.4-oss``.
The Redis service uses ``redis:8-alpine``.
The image's default ``PGDATA`` directory is ``/home/postgres/pgdata/data``; compose mounts the
``seed_pgdata`` volume at ``/home/postgres/pgdata`` so the container can manage its ``data``
subdirectory.
Existing volumes from older major Postgres versions cannot be started directly
with this image. If you need to keep data from an older Postgres volume, follow
the dump/restore process in :doc:`postgres_upgrade` before starting Postgres 18.
If you do not need the old data, recreate the database volume instead.

* Run Docker Compose

    .. code-block:: bash

        docker compose build

    `Be Patient`_ ... If the containers build successfully, then start the containers

    .. code-block:: bash

        docker volume create --name=seed_pgdata
        docker volume create --name=seed_media
        docker compose up

    **Note that you may need to build the containers a couple times for everything to converge**

* Login to container

    The Docker Compose file creates a default user and password. Below are the defaults but can
    be overridden by setting environment variables.

    .. code-block:: bash

        username: user@seed-platform.org
        password: super-secret-password


.. note::

    Don't forget that you need to reset your default username and password if you are going
    to use these Docker images in production mode!

Using Docker for Development
----------------------------

The development environment is configured for live reloading and debugging. It
builds from ``Dockerfile-dev`` and layers ``docker-compose.dev.yml`` on top of
the base ``docker-compose.yml``.

Build
^^^^^

.. code-block:: bash

    # create volumes for the database and media directory
    docker volume create --name=seed_pgdata
    docker volume create --name=seed_media

    # initialize the Angular UI submodule
    git submodule update --init ng_seed/seed-angular

    # build the images
    docker compose -f docker-compose.yml -f docker-compose.dev.yml build

Running the Server
^^^^^^^^^^^^^^^^^^

NOTE: the server config is sourced from config.settings.docker_dev, which will include
your local_untracked.py if it exists. If you have a local_untracked.py, make sure it doesn't
overwrite the database or celery configuration!

.. code-block:: bash

    docker compose -f docker-compose.yml -f docker-compose.dev.yml up

The AngularJS application is available at ``http://localhost/app/``. To see the
new Angular application at ``http://localhost/ng-app/``, build the Angular
assets and launch the container stack.

The health check is available at ``http://localhost/api/health_check/``. A
healthy container stack returns ``200 OK`` with ``postgres``, ``redis``, and
``celery`` all set to ``success``. If the endpoint returns ``418 I'm a Teapot``,
one of the required services is not connected; the JSON response identifies the
failing service.

If the server doesn't start successfully, and :code:`docker compose logs` doesn't help,
the Hypercorn dev server probably failed to start due to an error in your config or code.
Unfortunately docker application logging doesn't appear to work when the container is first started.
Just try running the server yourself with docker exec, and see what the output is.

The development Docker Compose file has some configurable parameters for specifying volumes to use:

- SEED_DB_VOLUME: the name of the docker volume to mount for postgres
- SEED_MEDIA_VOLUME: the name of the docker volume to mount for the seed media folder

Docker will use environment variables from the shell or from a .env file to set these values.

This is useful if you want to switch between different databases for testing.
For example, if you want to create a separate volume for storing a production backup, you could do the following

.. code-block:: bash

    docker volume create --name=seed_pgdata_prod
    SEED_DB_VOLUME=seed_pgdata_prod docker compose -f docker-compose.yml -f docker-compose.dev.yml up

NOTE: you'll need to run :code:`docker compose down` to remove the containers before you
can restart the containers connecting to different volumes.

Running Tests
^^^^^^^^^^^^^

While the containers are running (i.e., after running the docker compose up command), use docker exec to run tests in the web container:

.. code-block:: bash

    docker exec -it seed_web uv run manage.py test --settings config.settings.docker_test

Add the setting  :code:`--nocapture` in order to see :code:`stdout` while running tests.  You will need to do this in order to make use of debugging as described below or the output to your debug commands will not display until after the break point has passed and the tests are finished.

Also worth noting: output from logging (_log.debug, etc) will not display in any situation unless a test fails.

Debugging
^^^^^^^^^

To use pdb on the server, the web container has `remote-pdb <https://github.com/ionelmc/python-remote-pdb>`_ installed.
In your code, insert the following

.. code-block:: bash

    import remote_pdb; remote_pdb.set_trace()

Once the breakpoint is triggered, you should see the web container log something like "RemotePdb session open at 127.0.0.1:41653, waiting for connection ...".
To connect to the remote session, run netcat from inside the container (using the appropriate port).

.. code-block:: bash

    docker exec -it seed_web nc 127.0.0.1:41653

.. _Be Patient: https://www.youtube.com/watch?v=f4hkPn0Un_Q
