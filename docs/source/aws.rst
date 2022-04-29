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

Ubuntu server 18.04 LTS

.. note:: These instructions have not been updated for Ubuntu 18.04. It is recommended to use Docker-based deployments.

.. code-block:: console

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install -y libpq-dev python-dev python-pip libatlas-base-dev \
    gfortran build-essential g++ npm libxml2-dev libxslt1-dev git mercurial \
    libssl-dev libffi-dev curl uwsgi-core uwsgi-plugin-python


PostgreSQL and Redis are not included in the above commands. For a quick installation on AWS it
is okay to install PostgreSQL and Redis locally on the AWS instance. If a more permanent and
scalable solution, it is recommended to use AWS's hosted Redis (ElastiCache) and PostgreSQL service.

.. note:: postgresql ``>=9.4`` is required to support `JSON Type`_

.. code-block:: console

    # To install PostgreSQL and Redis locally
    sudo apt-get install redis-server
    sudo apt-get install postgresql postgresql-contrib

.. _`JSON Type`: https://www.postgresql.org/docs/9.4/datatype-json.html

Amazon Web Services (AWS) Dependencies
++++++++++++++++++++++++++++++++++++++

The following AWS services can be used for **SEED** but are not required:

* RDS (PostgreSQL >=9.4)
* ElastiCache (redis)
* SES


Python Dependencies
^^^^^^^^^^^^^^^^^^^

Clone the **SEED** repository from **github**

.. code-block:: console

    $ git clone git@github.com:SEED-platform/seed.git

enter the repo and install the python dependencies from `requirements`_

.. _requirements: https://github.com/SEED-platform/seed/blob/main/requirements/aws.txt

.. code-block:: console

    $ cd seed
    $ sudo pip install -r requirements/aws.txt


JavaScript Dependencies
^^^^^^^^^^^^^^^^^^^^^^^

``npm`` is required to install the JS dependencies.

.. code-block:: console

    $ sudo apt-get install build-essential
    $ sudo apt-get install curl


.. code-block:: console

    $ npm install


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
``local_untracked.py`` should be updated with the ``CACHES`` and ``CELERY_BROKER_URL``
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
    CELERY_BROKER_URL = 'redis://seed-core-cache.ntmprk.0001.usw2.cache.amazonaws.com:6379/1'

Running Celery the Background Task Worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Celery`_ is used for background tasks (saving data, matching, creating
projects, etc) and must be connected to the message broker queue. From the
project directory, ``celery`` can be started:

.. code-block:: console

    celery -A seed worker -l INFO -c 2 -B --events --max-tasks-per-child 1000

.. _Celery: http://www.celeryproject.org/
