=========
AWS Setup
=========

Amazon Web Services (`AWS`_) provides the preferred hosting for SEED.

**seed** is a `Django Project`_ and Django's documentation
is an excellent place for general understanding of this project's layout.

.. _Django Project: https://www.djangoproject.com/

.. _AWS: http://aws.amazon.com/

Prerequisites
^^^^^^^^^^^^^^

Ubuntu server 13.10 or newer, with the following list of *aptitude packages*
installed.

Copy the *prerequisites.txt* files to the server and install the dependencies:

.. code-block:: console

    $ sudo dpkg --set-selections < ./prerequisites.txt
    $ sudo apt-get dselect-upgrade

or with a single command as ``su``

.. code-block:: console

    # aptitude install $(cat ./prerequisites.txt | awk '{print $1}')

.. note::

    PostgresSQL server is not included above, and it is assumed that the system
    will use the AWS RDS PostgresSQL service

.. note:: postgresql ``>=9.3`` is required to support `JSON Type`_


.. _JSON Type: http://www.postgresql.org/docs/9.3/static/datatype-json.html


A smaller list of packages to get going:

.. code-block:: console

    $ sudo apt-get install python-pip python-dev libatlas-base-dev gfortran \
    python-dev build-essential g++ npm libxml2-dev libxslt1-dev \
    postgresql-devel postgresql-9.3 postgresql-server-dev-9.3 libpq-dev \
    libmemcached-dev openjdk-7-jre-headless



Amazon Web Services (AWS) Dependencies
++++++++++++++++++++++++++++++++++++++

The following AWS services are used for **seed**:

* RDS (PostgreSQL >=9.3)
* ElastiCache (redis)
* SES
* S3


Python Dependencies
^^^^^^^^^^^^^^^^^^^

Clone the **seed** repository from **github**

.. code-block:: console

    $ git clone git@github.com:SEED-platform/seed.git

enter the repo and install the python dependencies from `requirements`_

.. _requirements: https://github.com/SEED-platform/seed/blob/master/requirements/local.txt

.. code-block:: console

    $ cd seed
    $ sudo pip install -r requirements/local.txt


JavaScript Dependencies
^^^^^^^^^^^^^^^^^^^^^^^

``npm`` is required to install the JS dependencies. The ``bin/install_javascript_dependencies.sh`` script will
download all JavaScript dependencies and build them. ``bower`` and ``grunt-cli`` will be installed globally by
the ``install_javascript_dependencies`` script.  The Ubuntu version ``13.10`` requires a custom install of
nodejs/npm, and an install script (``bin/node-and-npm-in-30s.sh``) is provided to download a stable release and
install ``npm`` assuming the prerequisites are met.

.. code-block:: console

    $ sudo apt-get install build-essential
    $ sudo apt-get install libssl-dev
    $ sudo apt-get install curl
    $ . bin/node-and-npm-in-30s.sh


.. code-block:: console

    $ bin/install_javascript_dependencies.sh


Database Configuration
^^^^^^^^^^^^^^^^^^^^^^

Copy the ``local_untracked.py.dist`` file in the ``config/settings`` directory to
``config/settings/local_untracked.py``, and add a ``DATABASES`` configuration with your database username,
password, host, and port. Your database configuration can point to an AWS RDS instance or a PostgreSQL 9.4 database
instance you have manually installed within your infrastructure.

.. code-block:: python

    # Database
    DATABASES = {
        'default': {
            'ENGINE':'django.db.backends.postgresql_psycopg2',
            'NAME': 'seed',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    }


.. note::


    other databases could be used such as MySQL, but are not supported
    due to the postgres-specific `JSON Type`_

In in the above database configuration, ``seed`` is the database name, this
is arbitrary and any valid name can be used as long as the database exists.

create the database within the postgres ``psql`` shell:

.. code-block:: psql

    postgres-user=# CREATE DATABASE seed;

or from the command line:

.. code-block:: console

    $ createdb seed


create the database tables and migrations:

.. code-block:: console

    $ python manage.py syncdb
    $ python manage.py migrate

.. note::

    running migrations can be shortened into a one-liner ``./manage.py syncdb
    --migrate``

create a superuser to access the system

.. code-block:: console

    $ python manage.py create_default_user --username=demo@example.com --organization=example --password=demo123


.. note::

    Every user must be tied to an organization, visit ``/app/#/profile/admin``
    as the superuser to create parent organizations and add users to them.



cache and message broker
^^^^^^^^^^^^^^^^^^^^^^^^

The SEED project relies on `redis`_ for both cache and message brokering, and
is available as an AWS `ElastiCache`_ service.
``local_untracked.py`` should be updated with the ``CACHES`` and ``BROKER_URL``
settings.

.. _ElastiCache: https://aws.amazon.com/elasticache/

.. _redis: http://redis.io/


.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "seed-core-cache.ntmprk.0001.usw2.cache.amazonaws.com:6379",
            'OPTIONS': { 'DB': 1 },
            'TIMEOUT': 300
        }
    }
    BROKER_URL = 'redis://seed-core-cache.ntmprk.0001.usw2.cache.amazonaws.com:6379/1'

.. note::

    The popular ``memcached`` can also be used as a cache back-end, but is not
    supported and redis has a different cache key format, which could cause
    breakage and isn't tested.
    Likewise, ``rabbitmq`` or AWS ``SQS`` are alternative message brokers,
    which could cause breakage and is not tested.


running celery the background task worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Celery`_ is used for background tasks (saving data, matching, creating
projects, etc) and must be connected to the message broker queue. From the
project directory, ``celery`` can be started:

.. code-block:: console

    $ python manage.py celery worker -B -c 2 --loglevel=INFO -E --maxtasksperchild=1000


.. _Celery: http://www.celeryproject.org/


running the development web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Django dev server (not for production use) can be a quick and easy way to
get an instance up and running. The dev server runs by default on port 8000
and can be run on any port. See Django's `runserver documentation`_ for more
options.

.. _runserver documentation: https://docs.djangoproject.com/en/1.6/ref/django-admin/#django-admin-runserver

.. code-block:: console

    $ python manage.py runserver


running a production web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Our recommended web server is uwsgi sitting behind nginx. The
``bin/start_uwsgi.sh`` `script`_ can been created to start ``uwsgi`` assuming
your Ubuntu user is named ``ubuntu``.

Also, static assets will need to be moved to S3 for production use. The
``bin/post_compile`` script contains a list of commands to move assets to S3.

.. code-block:: console

    $ bin/post_compile

.. _script: https://github.com/SEED-platform/seed/blob/master/bin/start_uwsgi.sh

.. code-block:: console

    $ bin/start_uwsgi

The following environment variables can be set within the ``~/.bashrc`` file to
override default Django settings.

.. code-block:: bash

    export SENTRY_DSN=https://xyz@app.getsentry.com/123
    export DEBUG=False
    export ONLY_HTTPS=True

