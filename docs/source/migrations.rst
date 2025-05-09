Migrations
==========

Django handles the migration of the database very well; however, there are various changes to SEED that may require some custom (manual) migrations. The migration documentation includes the required changes based on deployment and development for each release.

Version Develop
---------------

In order to support Redis passwords, the configuration of the Redis/Celery settings changed a bit.
You will need to add the following to your local_untracked.py configuration file. If you are using
Docker then you will not need to do this.

.. code-block:: python

    CELERY_RESULT_BACKEND = CELERY_BROKER_URL

If you are using a password, then in your local_untracked.py configuration, add the password to
the CELERY_BROKER_URL. Your final configuration should look like the following in your
local_untracked.py file

.. code-block:: python

    CELERY_BROKER_URL = 'redis://:password@127.0.0.1:6379/1'
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': CELERY_BROKER_URL,
        }
    }

    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
    CELERY_TASK_DEFAULT_QUEUE = 'seed-local'
    CELERY_TASK_QUEUES = (
        Queue(
            CELERY_TASK_DEFAULT_QUEUE,
            Exchange(CELERY_TASK_DEFAULT_QUEUE),
            routing_key=CELERY_TASK_DEFAULT_QUEUE
        ),
    )

Version 3.2.5
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.2.4
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.2.3
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.2.2
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.2.1
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.2.0
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.1.0
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.0.0
-------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 3.0.0-beta.0
--------------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.22.0
--------------
- Run ``./manage.py migrate``.
- There is a Redis dependency update in this release that requires users and deployments to modify their settings' ``CACHES`` config.
   #. Update your dependencies with ``pip install -r requirements/base.txt``
   #. Update the CACHES BACKEND property to ``django_redis.cache.RedisCache``
   #. Update the CACHES LOCATION property to match the redis-py native URL notation for connection strings, including the redis protocol and database number. e.g. ``redis://localhost:6379/1``

   Since the CELERY_BROKER_URL setting must also be in the same format, it may be helpful to configure that setting first and then reference it in the caches LOCATION parameter.
- See the `PR for an example migration <https://github.com/SEED-platform/seed/pull/4376#issue-1972716522>`_.

Version 2.21.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.20.1
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.20.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.
- There is a single long running migration related to importing census tract disadvantaged community data. This migration should take around 7 minutes to complete.

Version 2.19.0
--------------
- Run `./manage.py migrate`.
- There is a new migration in this release that requires column names to be unique across `organization`, `table_name`, and `is_extra_data`. This migration will fail if there are duplicate column names. If you have duplicate column names, you will need to manually fix them in your database before running the migration. The following steps will help you identify and fix the duplicate column names:
    - Check the organization age to gauge the impact of the change. If it is a deprecated org, impact of the change will be low. Often this issue arose in older organizations when units were not part of the columns. The old mapping columns were not upserts with the units, so typically the columns impacted are the ones with units.
    - Query the `seed_column` table for the organization and column name displayed on the screen (e.g., `organization_id = 300 and column_name = 'Source EUI (kBtu/ft2)'`). If there is no `table_name` set, it is likely an import file column name and can easily be cleaned up without causing issues. In such cases, there will be two rows, and you want to keep the one with the `units_pint` column set.
    - More complex columns may require deleting or updating the `column_id` in the `seed_columnmapping_*` tables. If there is a foreign key constraint with `seed_columnmapping_*`, take note of the ID you want to remove and the ID you want it to be replaced with (preferably keep the one with units_pint).
    - If the constraint is on `seed_columnmapping_column_raw`:
        - The field should be an import file column (i.e., no `table_name` item). Query for the old column in `seed_columnmapping_column_raw` (e.g., `column_name = <old_id>`).
        - Replace the old ID with the new one. If it errors because it already exists, then the row can be deleted.
        - Return to the `seed_column` table and remove the old ID.
    - If the constraint is on `seed_columnmapping_column_mapped`:
        - The mapped column should have a `table_name` in the field. If not, it is likely an older organization.
        - If there is no `table_name`, remove the row from the `seed_columnmapping_column_mapped` table.
        - Return to the `seed_column` table and remove the old ID.

Version 2.18.1
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.18.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.17.4
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.17.3
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.17.2
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.17.1
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.17.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.16.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.15.2
--------------
- There are no migrations needed for this version.

Version 2.15.1
--------------
- There are no migrations needed for this version.

Version 2.15.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.14.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.13.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.12.0 - 2.12.4
-----------------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.11.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.10.0
--------------
- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

Version 2.7.3 to 2.9.0
----------------------
- The migrations should work without additional support. Simply run ``./manage.py migrate``.

Version 2.7.2
-------------
- The migrations should work without additional support. Simply run ``./manage.py migrate``. There are no manual migrations needed.
- Note the **Important Note** in Version 2.7.1 migration below which may require the need to run a "fake" migration

Version 2.7.1
-------------

- There are no special migrations needed for this version. Simply run ``./manage.py migrate``.

**Important Note:**

If upgrading from `< 2.7.0` to `>= 2.7.1` you may encounter a failed migration with ``0118_match_merge_link_all_orgs``.  This is expected if the database is several versions behind, and it effectively reorders migration 118 to run after all other migrations have completed to prepare your database to recognize properties and taxlots across multiple cycles.  Run the following code manually to fully migrate:

#. ``./manage.py migrate --fake seed 0118_match_merge_link_all_orgs``

#. ``./manage.py migrate``

#. ``./manage.py shell``

    .. code-block:: python

        from seed.lib.superperms.orgs.models import Organization
        from seed.utils.match import whole_org_match_merge_link

        for org in Organization.objects.all():
            whole_org_match_merge_link(org.id, 'PropertyState')
            whole_org_match_merge_link(org.id, 'TaxLotState')

Version 2.7.0
-------------

- This migration will run a match/merge/pair/link method upon migration. Make sure to run the migration manually and not inside of the docker container using the ./deploy.sh script.
- Make sure to backup the database before performing the migration.
- Run ``./manage.py migrate``.

Version 2.6.1
-------------

- The migrations should work without additional support. Simply run ``./manage.py migrate``. There are no manual migrations needed for the 2.6.1 release.


Version 2.6.0
-------------

Version 2.6.0 includes support for meters and time series data storage. In order to use this release
you must first install `TimescaleDB`_.

Docker-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^
Docker-based deployments shouldn't require running any additional commands for installation. The
timescaledb installation will happen automatically when updating the postgres container. Also,
the installation of the extension occurs in a Django migration.

Ubuntu
^^^^^^

.. code-block:: console

    sudo add-apt-repository ppa:timescale/timescaledb-ppa
    sudo apt update
    sudo apt install timescaledb-postgresql-10
    sudo timescaledb-tune
    sudo service postgresql restart

Max OSX
^^^^^^^

.. code-block:: console

   brew tap timescale/tap
   brew install timescaledb
   /usr/local/bin/timescaledb_move.sh
   timescaledb-tune
   brew services restart postgresql

Version 2.5.2
-------------

- There are no manual migrations that are needed. The ``./manage.py migrate`` command may take awhile to run since the migration requires the recalculation of all the normalized addresses to parse bldg correct and to cast the result as a string and not a bytestring.

Version 2.5.1
-------------

- The migrations should work by simply running ``./manage.py migrate``. There are no manual migrations needed for the 2.5.1 release.

Version 2.5.0
-------------

Docker-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^

- Add the MapQuest API key to your organization.
- On deployment, the error below is indicative that you need to install the extensions in the postgres database. Run `docker exec <postgres_container_id> update-postgis.sh`.

    django.db.utils.OperationalError: could not open extension control file "/usr/share/postgresql/11/extension/postgis.control": No such file or directory

- If you are using a copied version of the docker-compose.yml file, then you need to change `127.0.0.1:5000/postgres` to `127.0.0.1:5000/postgres-seed`

Development
^^^^^^^^^^^

- **Delete** your bower directory `rm -rf seed/static/vendors`.
- **Delete** your css directory `rm -rf seed/static/seed/css`.
- **Remove** these lines from `local_untracked.py` if you have them.

.. code-block:: python

    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    STATICFILES_STORAGE = DEFAULT_FILE_STORAGE

- Run `pip3 install -r requirements/local.txt`.
- Run `npm install` from root checkout of SEED.

- If testing geocoding, then sign up for as a `MapQuest Developer`_ and create a new `MapQuest Key`_.
- Add the key to the organization that you are using in development.

- **Update** your DATABASES engine to be `django.contrib.gis.db.backends.postgis`

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'seeddb',
            'USER': 'seeduser',
            'PASSWORD': 'seedpass',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

- Run ``./manage.py migrate``

.. _`MapQuest Developer`: https://developer.mapquest.com/plan_purchase/steps/business_edition/business_edition_free/register

.. _`MapQuest Key`: https://developer.mapquest.com/user/me/apps

.. _`TimescaleDB`: https://docs.timescale.com/v1.2/getting-started
