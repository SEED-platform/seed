=========
AWS Setup
=========

Amazon Web Services (`AWS`_) provides the preferred hosting for the SEED Platform.

**seed** is a `Django Project`_ and Django's documentation is an excellent place for general
understanding of this project's layout.

.. _Django Project: https://www.djangoproject.com/

.. _AWS: http://aws.amazon.com/

Prerequisites
^^^^^^^^^^^^^

Ubuntu server 14.04 or newer.

.. code-block:: console

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install -y libpq-dev python-dev python-pip libatlas-base-dev \
    gfortran build-essential g++ npm libxml2-dev libxslt1-dev git mercurial \
    libssl-dev curl uwsgi-core uwsgi-plugin-python


PostgreSQL and Redis are not included in the above commands. For a quick installation on AWS it
is okay to install PostgreSQL and Redis locally on the AWS instance. If a more permanent and
scalable solution, it is recommended to use AWS's hosted Redis (ElastiCache) and PostgreSQL service.

.. note:: postgresql ``>=9.4`` is required to support `JSON Type`_

.. code-block:: console

    # To install PostgreSQL and Redis locally
    sudo apt-get install redis-server
    sudo apt-get install postgresql postgresql-contrib


Amazon Web Services (AWS) Dependencies
++++++++++++++++++++++++++++++++++++++

The following AWS services are used for **SEED**:

* RDS (PostgreSQL >=9.4)
* ElastiCache (redis)
* SES


Python Dependencies
^^^^^^^^^^^^^^^^^^^

Clone the **SEED** repository from **github**

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
download all JavaScript dependencies and build them.  ``bower`` and ``gulp`` should be installed globally for
convenience.

.. code-block:: console

    $ sudo apt-get install build-essential
    $ sudo apt-get install curl


.. code-block:: console

    $ sudo npm install -g bower gulp
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

In the above database configuration, ``seed`` is the database name, this
is arbitrary and any valid name can be used as long as the database exists.

create the database within the postgres ``psql`` shell:

.. code-block:: psql

    CREATE DATABASE seed;

or from the command line:

.. code-block:: console

    createdb seed


create the database tables and migrations:

.. code-block:: console

    python manage.py syncdb
    python manage.py migrate


create a superuser to access the system

.. code-block:: console

    $ python manage.py create_default_user --username=demo@example.com --organization=example --password=demo123


.. note::

    Every user must be tied to an organization, visit ``/app/#/profile/admin``
    as the superuser to create parent organizations and add users to them.



Cache and Message Broker
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


Running Celery the Background Task Worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Celery`_ is used for background tasks (saving data, matching, creating
projects, etc) and must be connected to the message broker queue. From the
project directory, ``celery`` can be started:

.. code-block:: console

    celery -A seed worker -l INFO -c 2 -B --events --maxtasksperchild 1000

.. _Celery: http://www.celeryproject.org/


Running the Development Web Server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Django dev server (not for production use) can be a quick and easy way to
get an instance up and running. The dev server runs by default on port 8000
and can be run on any port. See Django's `runserver documentation`_ for more
options.

.. _runserver documentation: https://docs.djangoproject.com/en/1.6/ref/django-admin/#django-admin-runserver

.. code-block:: console

    $ ./manage.py runserver


Running a Production Web Server
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

