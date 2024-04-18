Installation using Docker
=========================

Docker works natively on Linux, Mac OSX, and Windows 10. If you are using an older version of
Windows (and some older versions of Mac OSX), you will need to install Docker Toolbox.

Choose either `Docker Native (Windows/OSX)`_  or `Docker Native (Ubuntu)`_ to
install Docker.

Docker Native (Ubuntu)
----------------------

Follow instructions `here <https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/>`_.

* `Install Docker Compose <https://docs.docker.com/compose/install/>`_


Docker Native (Windows/OSX)
---------------------------

Following instructions `for Mac <https://docs.docker.com/docker-for-mac/install/>`_ or
`for Windows <https://docs.docker.com/docker-for-windows/install/>`_. Note that for OSX you must have docker desktop version `3.0 or later <https://github.com/concourse/concourse/issues/6038>`.

* `Install Docker Compose <https://docs.docker.com/compose/install/>`_


Building and Running Containers for Non-Development
-------------------------------------------------------

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

    The docker-compose file creates a default user and password. Below are the defaults but can
    be overridden by setting environment variables.

    .. code-block:: bash

        username: user@seed-platform.org
        password: super-secret-password


.. note::

    Don't forget that you need to reset your default username and password if you are going
    to use these Docker images in production mode!

Using Docker for Development
----------------------------

The development environment is configured for live reloading (i.e., restart webserver when files change)
and debugging. It builds off the base docker-compose.yml, so it's necessary
to specify the files being used in docker-compose commands as seen below.

Build
^^^^^

.. code-block:: bash

    # create volumes for the database and media directory
    docker volume create --name=seed_pgdata
    docker volume create --name=seed_media

    # build the images
    docker compose -f docker-compose.yml -f docker-compose.dev.yml build

Running the Server
^^^^^^^^^^^^^^^^^^

NOTE: the server config is sourced from config.settings.docker_dev, which will include
your local_untracked.py if it exists. If you have a local_untracked.py, make sure it doesn't
overwrite the database or celery configuration!

.. code-block:: bash

    docker compose -f docker-compose.yml -f docker-compose.dev.yml up

If the server doesn't start successfully, and :code:`docker compose logs` doesn't help,
the django development server probably failed to start due to an error in your config or code.
Unfortunately docker/django logging doesn't appear to work when the container is first started.
Just try running the server yourself with docker exec, and see what the output is.

The development docker-compose file has some configurable parameters for specifying volumes to use:

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

    docker exec -it seed_web ./manage.py test --settings config.settings.docker_dev

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

.. _MacPorts: https://www.macports.org/
.. _Homebrew: http://brew.sh/
.. _npm: https://www.npmjs.com/
.. _nodejs.org: http://nodejs.org/
.. _Be Patient: https://www.youtube.com/watch?v=f4hkPn0Un_Q
