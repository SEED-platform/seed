Migrations
==========

Django handles the migration of the database very well; however, there are various changes to SEED that may require some custom (manual) migrations. The migration documenation includes the required changes based on deployment and development for each release.

Version 2.5.0
-------------

Docker-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^

- Add your MapQuest Key, `MAPQUEST_API_KEY`, to the docker-compose file that is used for deployment. You can also add the MapQuest API key to your organization.

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
- Add the key to either your local_untracked.py file or as an environment variables `MAPQUEST_API_KEY`.

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
