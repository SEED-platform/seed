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

Ubuntu server 14.04 or newer

Install the following base packages to run SEED:

.. code-block:: console

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install libpq-dev python-dev python-pip libatlas-base-dev \
    gfortran build-essential g++ npm libxml2-dev libxslt1-dev git mercurial \
    libssl-dev curl uwsgi-core uwsgi-plugin-python
    sudo apt-get install redis-server
    sudo apt-get install postgresql postgresql-contrib


.. note:: postgresql ``>=9.3`` is required to support `JSON Type`_

.. _JSON Type: http://www.postgresql.org/docs/9.3/static/datatype-json.html

Configure PostgreSQL
^^^^^^^^^^^^^^^^^^^^

.. code-block:: console

    $ sudo su - postgres
    $ createdb "seed-deploy"
    $ createuser -P DBUsername
    $ psql
    postgres=# GRANT ALL PRIVILEGES ON DATABASE "seed-deploy" TO DBUsername;
    postgres=# \q
    $ exit

.. note:: Any database name and username can be used here in place of "seed-deploy" and DBUsername




Python Dependencies
^^^^^^^^^^^^^^^^^^^

clone the **seed** repository from **github**

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
download all JavaScript dependencies and build them. ``bower`` and ``gulp`` should be installed globally for
convenience.

.. code-block:: console

    $ curl -sL https://deb.nodesource.com/setup_5.x | sudo -E bash -
    $ sudo apt-get install -y nodejs
    $ sudo npm install -g bower gulp


.. code-block:: console

    $ bin/install_javascript_dependencies.sh


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
            'ENGINE':'django.db.backends.postgresql_psycopg2',
            'NAME': 'seed-deploy',
            'USER': 'DBUsername',
            'PASSWORD': '',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }


.. note::

    Other databases could be used such as MySQL, but are not supported
    due to the postgres-specific `JSON Type`_

In in the above database configuration, ``seed`` is the database name, this is arbitrary and any valid name can be
used as long as the database exists. Enter the database name, user, password you set above.

The database settings can be tested using the Django management command, ``./manage.py dbshell`` to connect to the
configured database.

create the database tables and migrations:

.. code-block:: console

    $ python manage.py migrate

Cache and Message Broker
^^^^^^^^^^^^^^^^^^^^^^^^

The SEED project relies on `redis`_ for both cache and message brokering, and
is available as an AWS `ElastiCache`_ service or with the ``redis-server``
Linux package. (``sudo apt-get install redis-server``)

``local_untracked.py`` should be updated with the ``CACHES`` and ``CELERY_BROKER_URL``
settings.

.. _ElastiCache: https://aws.amazon.com/elasticache/

.. _redis: http://redis.io/


.. code-block:: python

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "127.0.0.1:6379",
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }
    CELERY_BROKER_URL = 'redis://127.0.0.1:6379/1'


Creating the initial user
^^^^^^^^^^^^^^^^^^^^^^^^^

create a superuser to access the system

.. code-block:: console

    $ python manage.py create_default_user --username=demo@example.com --organization=example --password=demo123


.. note::

    Every user must be tied to an organization, visit ``/app/#/profile/admin``
    as the superuser to create parent organizations and add users to them.



Running celery the background task worker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Celery`_ is used for background tasks (saving data, matching, creating
projects, etc) and must be connected to the message broker queue. From the
project directory, ``celery`` can be started:

.. code-block:: console

    celery -A seed worker -l INFO -c 2 -B --events --maxtasksperchild 1000

.. _Celery: http://www.celeryproject.org/


Running the development web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Django dev server (not for production use) can be a quick and easy way to
get an instance up and running. The dev server runs by default on port 8000
and can be run on any port. See Django's `runserver documentation`_ for more
options.

.. _runserver documentation: https://docs.djangoproject.com/en/1.6/ref/django-admin/#django-admin-runserver

.. code-block:: console

    $ python manage.py runserver --settings=config.settings.dev


Running a production web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Our recommended web server is uwsgi sitting behind nginx. The python package ``uwsgi`` is needed for this, and
should install to ``/usr/local/bin/uwsgi`` Since AWS S3, is not being used here, we recommend using ``dj-static``
to load static files.

.. note::

    The use of the ``dev`` settings file is production ready, and should be
    used for non-AWS installs with ``DEBUG`` set to ``False`` for production use.


.. code-block:: console

    $ sudo pip install uwsgi dj-static


Generate static files:

.. code-block:: console

    $ sudo ./manage.py collectstatic --settings=config.settings.dev

Update ``config/settings/local_untracked.py``:

.. code-block:: python

    DEBUG = False
    # static files
    STATIC_ROOT = 'collected_static'
    STATIC_URL = '/static/'

Start the web server:

.. code-block:: console

    $ sudo /usr/local/bin/uwsgi --http :80 --module standalone_uwsgi --max-requests 5000 --pidfile /tmp/uwsgi.pid --single-interpreter --enable-threads --cheaper-initial 1 -p 4

.. warning::

    Note that uwsgi has port set to ``80``. In a production setting, a dedicated web server such as NGINX would be
    receiving requests on port 80 and passing requests to uwsgi running on a different port, e.g 8000.




Environmental Variables
^^^^^^^^^^^^^^^^^^^^^^^

The following environment variables can be set within the ``~/.bashrc`` file to
override default Django settings.

.. code-block:: bash

    export SENTRY_DSN=https://xyz@app.getsentry.com/123
    export DEBUG=False
    export ONLY_HTTPS=True


SMTP service
^^^^^^^^^^^^

In the AWS setup, we can use SES to provide an email service for Django. The service is
configured in the config/settings/main.py:

.. code-block:: python

    EMAIL_BACKEND = 'django_ses.SESBackend'

Many options for setting up your own SMTP service/server or using other SMTP
third party services are available and compatible including `gmail`_.

.. _gmail: http://stackoverflow.com/questions/19264907/python-django-gmail-smtp-setup

Django can likewise send emails via python's smtplib with sendmail or postfix
installed. See their `docs`_ for more info.

.. _docs: https://docs.djangoproject.com/en/1.6/topics/email/

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
    DOMAIN_URLCONFS = {}
    DOMAIN_URLCONFS['default'] = 'urls.main'

    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "127.0.0.1:6379",
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
