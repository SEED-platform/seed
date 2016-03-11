Installation on Docker
======================

.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.org/en/latest/
.. _MacPorts: https://www.macports.org/
.. _Homebrew: http://brew.sh/
.. _npm: https://www.npmjs.com/
.. _nodejs.org: http://nodejs.org/
.. _Docker-Toolbox: https://docs.docker.com/toolbox/overview/
.. _Docker: https://docs.docker.com/installation/
.. _Docker-Machine: https://docs.docker.com/machine/install-machine/
.. _Docker-Compose: https://docs.docker.com/compose/install/
.. _Be Patient: https://www.youtube.com/watch?v=f4hkPn0Un_Q

Install Docker Toolbox
----------------------

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
