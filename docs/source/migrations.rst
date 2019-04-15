Migrations
==========

Django handles the migration of the database very well; however, there are various changes to SEED that may require some custom (manual) migrations. The migration documenation includes the required changes based on deployment and development for each release.

Version 2.6.0-Beta
------------------

2.6.0-beta includes support for meters and time series data storage. In order to use this release
you must first install [timescaledb](https://docs.timescale.com/v1.2/getting-started).


Version 2.5.1
-------------

- The migrations should work by simply running `./manage.py migrate`. There are no manual migrations needed for the 2.5.1 release.

Version 2.5.0
-------------

Docker-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^

- Add the MapQuest API key to your organization.
- On deployment, the error below is indicative that you need to install the extensions in the postgres database. Run `docker exec <posgres_container_id> update-postgis.sh`.

    django.db.utils.OperationalError: could not open extension control file "/usr/share/postgresql/11/extension/postgis.control": No such file or directory

- If you are using a copied version of the docker-compose.yml file (e.g., for OEP support), then you need to change `127.0.0.1:5000/postgres` to `127.0.0.1:5000/postgres-seed`

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

.. code-block:: json

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

- Run `./manage.py migrate`

.. _`MapQuest Developer`: https://developer.mapquest.com/plan_purchase/steps/business_edition/business_edition_free/register

.. _`MapQuest Key`: https://developer.mapquest.com/user/me/apps
