General Linux Setup
===================

While Amazon Web Services (`AWS`_) provides the preferred hosting for SEED,
running on a bare-bones Linux server follows a similar setup, replacing the
AWS services with their Linux package counterparts, namely: PostgreSQL and
Redis.

**SEED** is a `Django project`_ and Django's documentation
is an excellent place to general understanding of this project's layout.

.. _Django project: https://www.djangoproject.com/

.. _AWS: http://aws.amazon.com/

Prerequisites
^^^^^^^^^^^^^^

Ubuntu server/desktop 16.04 or newer (18.04 recommended)

Install the following base packages to run SEED:

.. code-block:: console

    sudo add-apt-repository ppa:timescale/timescaledb-ppa
    sudo apt update
    sudo apt upgrade
    sudo apt install libpq-dev python3-dev python3-pip libatlas-base-dev \
    gfortran build-essential nodejs npm libxml2-dev libxslt1-dev git \
    libssl-dev libffi-dev curl uwsgi-core uwsgi-plugin-python mercurial
    sudo apt install gdal-bin postgis
    sudo apt install redis-server
    sudo apt install timescaledb-postgresql-10 postgresql-contrib

    # For running selenium/protractor
    sudo apt install default-jre

.. note:: postgresql ``>=9.3`` is required to support `JSON Type`_

.. _JSON Type: http://www.postgresql.org/docs/9.3/static/datatype-json.html

Configure PostgreSQL
^^^^^^^^^^^^^^^^^^^^

Replace 'seeddb', 'seeduser' with desired db/user. By
default use password `seedpass` when prompted

.. code-block:: console

    $ sudo timescaledb-tune
    $ sudo service postgresql restart
    $ sudo su - postgres
    $ createuser -P "seeduser"
    $ createdb "seeddb" --owner="seeduser"
    $ psql
    postgres=# GRANT ALL PRIVILEGES ON DATABASE "seeddb" TO "seeduser";
    postgres=# ALTER USER "seeduser" CREATEDB CREATEROLE SUPERUSER;
    postgres=# \q
    $ exit


Python Dependencies
^^^^^^^^^^^^^^^^^^^

clone the **seed** repository from **github**

.. code-block:: console

    $ git clone git@github.com:SEED-platform/seed.git

enter the repo and install the python dependencies from `requirements`_

.. _requirements: https://github.com/SEED-platform/seed/blob/main/requirements/local.txt

.. code-block:: console

    $ cd seed
    $ pip3 install -r requirements/local.txt


JavaScript Dependencies
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    $ npm install


Django Database Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy the ``local_untracked.py.dist`` file in the ``config/settings`` directory to
``config/settings/local_untracked.py``, and add a ``DATABASES`` configuration with your database username, password,
host, and port. Your database configuration can point to an AWS RDS instance or a PostgreSQL 9.4 database instance
you have manually installed within your infrastructure.

.. code-block:: python

    # Database
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'seeddb',
            'USER': 'seeduser',
            'PASSWORD': '<PASSWORD>',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }


.. note::

    Other databases could be used such as MySQL, but are not supported
    due to the postgres-specific `JSON Type`_

In in the above database configuration, ``seed`` is the database name, this is arbitrary and any valid name can be
used as long as the database exists. Enter the database name, user, password you set above.

The database settings can be tested using the Django management command, ``python3 manage.py dbshell`` to connect to the
configured database.

create the database tables and migrations:

.. code-block:: console

    $ python3 manage.py migrate

Cache and Message Broker
^^^^^^^^^^^^^^^^^^^^^^^^

The SEED project relies on `redis`_ for both cache and message brokering, and
is available as an AWS `ElastiCache`_ service or with the ``redis-server``
Linux package. (``sudo apt install redis-server``)

``local_untracked.py`` should be updated with the ``CACHES`` and ``CELERY_BROKER_URL``
settings.

.. _ElastiCache: https://aws.amazon.com/elasticache/

.. _redis: http://redis.io/


.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': '127.0.0.1:6379',
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }
    CELERY_BROKER_URL = 'redis://127.0.0.1:6379/1'


Creating the initial user
^^^^^^^^^^^^^^^^^^^^^^^^^

create a superuser to access the system

.. code-block:: console

    $ python3 manage.py create_default_user --username=admin@my.org --organization=lbnl --password=badpass


.. note::

    Of course, you need to save this user/password somewhere, since this is what
    you will use to login to the SEED website.

    Every user must be tied to an organization, visit ``/app/#/profile/admin``
    as the superuser to create parent organizations and add users to them.



Running celery the background task worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Celery`_ is used for background tasks (saving data, matching, data quality checks, etc.)
and must be connected to the message broker queue. From the project directory, ``celery``
can be started:

.. code-block:: console

    DJANGO_SETTINGS_MODULE=config.settings.dev celery -A seed worker -l INFO -c 2 --max-tasks-per-child 1000 -EBS django_celery_beat.schedulers:DatabaseScheduler

.. _Celery: http://www.celeryproject.org/


Running the development web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Django dev server (not for production use) can be a quick and easy way to
get an instance up and running. The dev server runs by default on port 8000
and can be run on any port. See Django's `runserver documentation`_ for more
options.

.. _runserver documentation: https://docs.djangoproject.com/en/1.6/ref/django-admin/#django-admin-runserver

.. code-block:: console

    $ python3 manage.py runserver --settings=config.settings.dev


Running a production web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Our recommended web server is uwsgi sitting behind nginx. The python package ``uwsgi`` is needed for this, and
should install to ``/usr/local/bin/uwsgi`` We recommend using ``dj-static`` to load static files.

.. note::

    The use of the ``dev`` settings file is production ready, and should be
    used for non-AWS installs with ``DEBUG`` set to ``False`` for production use.


.. code-block:: console

    $ pip3 install uwsgi dj-static


Generate static files:

.. code-block:: console

    $ python3 manage.py collectstatic --settings=config.settings.prod -i package.json -i npm-shrinkwrap.json -i node_modules/openlayers-ext/index.html

Update ``config/settings/local_untracked.py``:

.. code-block:: python

    DEBUG = False
    # static files
    STATIC_ROOT = 'collected_static'
    STATIC_URL = '/static/'

Start the web server (this also starts celery):

.. code-block:: console

    $ ./bin/start-seed

.. warning::

    Note that uwsgi has port set to ``80``. In a production setting, a dedicated web server such as NGINX would be
    receiving requests on port 80 and passing requests to uwsgi running on a different port, e.g 8000.




Environment Variables
^^^^^^^^^^^^^^^^^^^^^

The following environment variables can be set within the ``~/.bashrc`` file to
override default Django settings.

.. code-block:: bash

    export SENTRY_DSN=https://xyz@app.getsentry.com/123
    export DEBUG=False
    export ONLY_HTTPS=True


Mail Services
^^^^^^^^^^^^^

AWS SES Service
---------------

In the AWS setup, we can use SES to provide an email service for Django. The service is
configured in the config/settings/local_untracked.py:

.. code-block:: python

    EMAIL_BACKEND = 'django_ses.SESBackend'


In general, the following steps are needed to configure SES:

1. Access Amazon SES Console  - `Quickstart <https://docs.aws.amazon.com/ses/latest/DeveloperGuide/quick-start.html>`_
2. Login to Amazon SES Console. Verify which region we are using (e.g., us-east-1)
3. Decide on email address that will be sending the emails and add them to the `SES Verified Emails <https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.html>`_.
4. Test that SES works as expected (while in the SES sandbox). Note that you will need to add the sender and recipient emails to the verified emails while in the sandbox.
5. Update the local_untracked.py file or set the environment variables for the docker file.
6. Once ready, move the SES instance out of the sandbox. Following instructions `here <https://docs.aws.amazon.com/ses/latest/DeveloperGuide/request-production-access.html>`_
7. (Optional) Set up Amazon Simple Notification Service (Amazon SNS) to notify you of bounced emails and other issues.
8. (Optional) Use the AWS Management Console to set up Easy DKIM, which is a way to authenticate your emails. Amazon SES console will have the values for SPF and DKIM that you need to put into your DNS.

SMTP service
------------

Many options for setting up your own `SMTP`_ service/server or using other SMTP
third party services are available and compatible including `gmail`_. SMTP is not configured for working within Docker at the moment.

.. _SMTP: https://docs.djangoproject.com/en/2.0/ref/settings/#email-backend
.. _gmail: http://stackoverflow.com/questions/19264907/python-django-gmail-smtp-setup

.. code-block:: python

    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

local_untracked.py
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # PostgreSQL DB config
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'seed',
            'USER': 'your-username',
            'PASSWORD': 'your-password',
            'HOST': 'your-host',
            'PORT': 'your-port',
        }
    }

    # config for local storage backend
    DOMAIN_URLCONFS = {'default': 'config.urls'}

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': '127.0.0.1:6379',
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }
    CELERY_BROKER_URL = 'redis://127.0.0.1:6379/1'

    # SMTP config
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

    # static files
    STATIC_ROOT = 'collected_static'
    STATIC_URL = '/static/'
