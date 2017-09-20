Installation using Docker
======================

Docker works natively on Linux, Mac OSX, and Windows 10. If you are using an older version of
Windows (and some older versions of Mac OSX), you will need to install Docker Toolbox.

Choose either `Docker Toolbox`_, `Docker Native (Windows/OSX)`_,  or `Docker Native (Ubuntu)`_ to
install Docker.

Docker Toolbox
--------------

Install Docker-Toolbox_, which installs several applications including Docker, Docker Machine,
and Docker Compose.

* Create Docker-Machine Image

    The command below will create a 100GB volume for development. This is a very large volume and can be adjusted. Make sure to create a volume greater than 30GB.

    .. code-block:: bash

        docker-machine create --virtualbox-disk-size 100000 -d virtualbox dev

* Start Docker-Machine Image

    .. code-block:: bash

        docker-machine start dev  # if not already running
        # export environment variables
        eval $(docker-machine env dev)

* Get the Docker IP address (`docker-machine ip dev`)


Docker Native (Ubuntu)
----------------------

Follow instructions [here](https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/).

* [Install Docker Compose](https://docs.docker.com/compose/install/)


Docker Native (Windows/OSX)
---------------------------

Following instructions (for Mac)[https://docs.docker.com/docker-for-mac/install/] or
(for Windows)[https://docs.docker.com/docker-for-windows/install/].

* [Install Docker Compose](https://docs.docker.com/compose/install/)


Building and Configuring Containers
-----------------------------------

* Run Docker Compose

    .. code-block:: bash

        docker-compose build

    `Be Patient`_ ... If the containers build successfully, then start the containers

    .. code-block:: bash

        docker-compose up

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

.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/
.. _MacPorts: https://www.macports.org/
.. _Homebrew: http://brew.sh/
.. _npm: https://www.npmjs.com/
.. _nodejs.org: http://nodejs.org/
.. _Docker-Toolbox: https://docs.docker.com/toolbox/overview/
.. _Be Patient: https://www.youtube.com/watch?v=f4hkPn0Un_Q
