Developer Resources
===================

General Notes
-------------

Flake Settings
^^^^^^^^^^^^^^

Flake is used to statically verify code syntax. If the developer is running
flake from the command line, they should ignore the following checks in order
to emulate the same checks as the CI machine.

+------+--------------------------------------------------+
| Code | Description                                      |
+======+==================================================+
| E402 | module level import not at top of file           |
+------+--------------------------------------------------+
| E501 | line too long (82 characters) or max-line = 100  |
+------+--------------------------------------------------+
| E731 | do not assign a lambda expression, use a def     |
+------+--------------------------------------------------+
| W503 | line break occurred before a binary operator     |
+------+--------------------------------------------------+
| W504 | line break occurred after a binary operator      |
+------+--------------------------------------------------+

To run flake locally call:

.. code-block:: console

    tox -e flake8

Django Notes
------------

Adding New Fields to Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Adding new fields to SEED can be complicated since SEED has a mix of typed fields (database fields) and extra data
fields. Follow the steps below to add new fields to the SEED database:

#. Add the field to the PropertyState or the TaxLotState model. Adding fields to the Property or TaxLot models is more complicated and not documented yet.
#. Add field to list in the following locations:

- models/columns.py: Column.DATABASE_COLUMNS
- TaxLotState.coparent or PropertyState.coparent: SQL query and keep_fields

#. Run `./manage.py makemigrations`
#. Add in a Python script in the new migration to add in the new column into every organizations list of columns. Note that the new_db_fields will be the same as the data in the Column.DATABASE_COLUMNS that were added.

    .. code-block:: python

        def forwards(apps, schema_editor):
            Column = apps.get_model("seed", "Column")
            Organization = apps.get_model("orgs", "Organization")

            new_db_fields = [
                {
                    'column_name': 'geocoding_confidence',
                    'table_name': 'PropertyState',
                    'display_name': 'Geocoding Confidence',
                    'data_type': 'number',
                }, {
                    'column_name': 'geocoding_confidence',
                    'table_name': 'TaxLotState',
                    'display_name': 'Geocoding Confidence',
                    'data_type': 'number',
                }
            ]

            # Go through all the organizatoins
            for org in Organization.objects.all():
                for new_db_field in new_db_fields:
                    columns = Column.objects.filter(
                        organization_id=org.id,
                        table_name=new_db_field['table_name'],
                        column_name=new_db_field['column_name'],
                        is_extra_data=False,
                    )

                    if not columns.count():
                        new_db_field['organization_id'] = org.id
                        Column.objects.create(**new_db_field)
                    elif columns.count() == 1:
                        # If the column exists, then just update the display_name and data_type if empty
                        c = columns.first()
                        if c.display_name is None or c.display_name == '':
                            c.display_name = new_db_field['display_name']
                        if c.data_type is None or c.data_type == '' or c.data_type == 'None':
                            c.data_type = new_db_field['data_type']
                        c.save()
                    else:
                        print("  More than one column returned")


        class Migration(migrations.Migration):
            dependencies = [
                ('seed', '0090_auto_20180425_1154'),
            ]

            operations = [
                ... existing db migrations ...,
                migrations.RunPython(forwards),
            ]


#. Run migrations `./manage.py migrate`
#. Run unit tests, fix failures. Below is a list of files that need to be fixed (this is not an exhaustive list)

- test_mapping_data.py:test_keys
- test_columns.py:test_column_retrieve_schema
- test_columns.py:test_column_retrieve_db_fields

#. (Optional) Update example files to include new fields
#. Test import workflow with mapping to new fields


AngularJS Integration Notes
---------------------------

Template Tags
^^^^^^^^^^^^^

Angular and Django both use `{{` and `}}` as variable delimiters, and thus the AngularJS variable delimiters are
renamed `{$` and `$}`.

.. code-block:: JavaScript

    window.BE.apps.seed = angular.module('BE.seed', ['$interpolateProvider'], function ($interpolateProvider) {
            $interpolateProvider.startSymbol("{$");
            $interpolateProvider.endSymbol("$}");
        }
    );

Django CSRF Token and AJAX Requests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For ease of making angular `$http` requests, we automatically add the CSRF token to all `$http` requests as
recommended by http://django-angular.readthedocs.io/en/latest/integration.html#xmlhttprequest

.. code-block:: JavaScript

    window.BE.apps.seed.run(function ($http, $cookies) {
        $http.defaults.headers.common['X-CSRFToken'] = $cookies['csrftoken'];
    });


Routes and Partials or Views
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Routes in `static/seed/js/seed.js` (the normal angularjs `app.js`)


.. code-block:: JavaScript

  SEED_app.config(['stateHelperProvider', '$urlRouterProvider', '$locationProvider', function (stateHelperProvider, $urlRouterProvider, $locationProvider) {
    stateHelperProvider
      .state({
        name: 'home',
        url: '/',
        templateUrl: static_url + 'seed/partials/home.html'
      })
      .state({
        name: 'profile',
        url: '/profile',
        templateUrl: static_url + 'seed/partials/profile.html',
        controller: 'profile_controller',
        resolve: {
          auth_payload: ['auth_service', '$q', 'user_service', function (auth_service, $q, user_service) {
            var organization_id = user_service.get_organization().id;
            return auth_service.is_authorized(organization_id, ['requires_superuser']);
          }],
          user_profile_payload: ['user_service', function (user_service) {
            return user_service.get_user_profile();
          }]
        }
      });
  }]);

HTML partials in `static/seed/partials/`

Logging
-------

Information about error logging can be found here - https://docs.djangoproject.com/en/1.7/topics/logging/

Below is a standard set of error messages from Django.

A logger is configured to have a log level. This log level describes the severity of
the messages that the logger will handle. Python defines the following log levels:

.. code-block:: console

    DEBUG: Low level system information for debugging purposes
    INFO: General system information
    WARNING: Information describing a minor problem that has occurred.
    ERROR: Information describing a major problem that has occurred.
    CRITICAL: Information describing a critical problem that has occurred.

Each message that is written to the logger is a Log Record. The log record is stored
in the web server & Celery


BEDES Compliance and Managing Columns
-------------------------------------

Columns that do not represent hardcoded fields in the application are represented using
a Django database model defined in the seed.models module. The goal of adding new columns
to the database is to create seed.models.Column records in the database for each column to
import. Currently, the list of Columns is dynamically populated by importing data.

There are default mappings for ESPM are located here:

    https://github.com/SEED-platform/seed/blob/develop/seed/lib/mappings/data/pm-mapping.json


Resetting the Database
----------------------

This is a brief description of how to drop and re-create the database
for the seed application.

The first two commands below are commands distributed with the
Postgres database, and are not part of the seed application. The third
command below will create the required database tables for seed and
setup initial data that the application expects (initial columns for
BEDES). The last command below (spanning multiple lines) will create a
new superuser and organization that you can use to login to the
application, and from there create any other users or organizations
that you require.

Below are the commands for resetting the database and creating a new
user:

.. code-block:: console

    createuser -U seed seeduser

    psql -c 'DROP DATABASE "seeddb"'
    psql -c 'CREATE DATABASE "seeddb" WITH OWNER = "seeduser";'
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seeddb" TO seeduser;'
    psql -c 'ALTER USER "seeduser" CREATEDB CREATEROLE SUPERUSER;'
    psql -d seeddb -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
    psql -d seeddb -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'
    psql -d seeddb -c 'SELECT timescaledb_pre_restore();'
    psql -d seeddb -c 'SELECT timescaledb_post_restore();'

    ./manage.py migrate
    ./manage.py create_default_user \
        --username=demo@seed-platform.org \
        --password=password \
        --organization=testorg

Restoring a Database Dump
-------------------------

.. code-block:: console

    psql -c 'DROP DATABASE "seeddb";'
    psql -c 'CREATE DATABASE "seeddb" WITH OWNER = "seeduser";'
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seeddb" TO "seeduser";'
    psql -c 'ALTER USER "seeduser" CREATEDB CREATEROLE SUPERUSER;'
    psql -d seeddb -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
    psql -d seeddb -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'
    psql -d seeddb -c 'SELECT timescaledb_pre_restore();'

    # restore a previous database dump (must be pg_restore 12+)
    /usr/lib/postgresql/12/bin/pg_restore -U seeduser -d seeddb /backups/prod-backups/seedv2_20191203_000002.dump

    psql -d seeddb -c 'SELECT timescaledb_post_restore();'

    ./manage.py migrate

    # if needed add a user to the database
    ./manage.py create_default_user \
        --username=demo@seed-platform.org \
        --password=password \
        --organization=testorg


Migrating the Database
----------------------

Migrations are handles through Django; however, various versions have customs actions for the migrations. See the :doc:`migrations page <migrations>` for more information based on the version of SEED.


Testing
-------

JS tests can be run with Jasmine at the url `/angular_js_tests/`.

Python unit tests are run with

.. code-block:: console

    python manage.py test --settings=config.settings.test

Note on geocode-related testing:
    Most of these tests use VCR.py and cassettes to capture and reuse recordings of HTTP requests and responses. Given that, unless you want to make changes and/or refresh the cassettes/recordings, there isn't anything needed to run the geocode tests.

    In the case that the geocoding logic/code is changed or you'd like to the verify the MapQuest API is still working as expected, you'll need to run the tests with a small change. Namely, you'll want to provide the tests with an API key via an environment variable called "TESTING_MAPQUEST_API_KEY" or within your local_untracked.py file with that same variable name.

    In order to refresh the actual cassettes, you'll just need to delete or move the old ones which can be found at ".seed/tests/data/vcr_cassettes". The API key should be hidden within the cassettes, so these new cassettes can and should be pushed to GitHub.

Run coverage using

.. code-block:: console

    coverage run manage.py test --settings=config.settings.test
    coverage report --fail-under=83

Python compliance uses PEP8 with flake8

.. code-block:: console

    flake8
    # or
    tox -e flake8

JS Compliance uses jshint

.. code-block:: console

    jshint seed/static/seed/js

Best Practices
--------------

1. Make sure there is an issue created for items you are working on (for tracking purposes and so that the item appears in the changelog for the release)
2. Use the following labels on the GitHub issue:
    **Feature** (features will appear as “New” item in the changelog)
    **Enhancement** (these will appear as “Improved" in the changelog)
    **Bug** (these will appear as “Fixed” in the changelog)
3. Move the ticket/issue to ‘In Progress’ in the GitHub project tracker when you begin work
4. Branch off of the ‘develop’ branch (unless it’s a hotfix for production)
5. Write a test for the code added.
6. Make sure to test locally.  note that all branches created and pushed to GitHub will also be tested automatically.
7. When done, create a pull request (you can group related issues together in the same PR).  Assign a reviewer to look over the code
8. Use the “DO NOT MERGE” label for Pull Requests that should not be merged
9. When PR has been reviewed and approved, move the ticket/issue to the 'Ready to Deploy to Dev' box in the GitHub project tracker.

Release Instructions
--------------------

To make a release do the following:

1. Github admin user, on develop branch: update the ``package.json`` file with the most recent version number. Always use MAJOR.MINOR.RELEASE.
2. Update the ``docs/sources/migrations.rst`` file with any required actions.
3. Run the ``docs/scripts/change_log.py`` script and add the changes to the CHANGELOG.md file for the range of time between last release and this release. Only add the *Closed Issues*. Also make sure that all the pull requests have a related Issue in order to be included in the change log.

.. code-block:: console

    python docs/scripts/change_log.py –k GITHUB_API_TOKEN –s 2018-02-26 –e 2018-05-30

4. Paste the results (remove unneeded Accepted Pull Requests) into the CHANGELOG.md. Make sure to cleanup the formatting.
5. Make sure that any new UI needing localization has been tagged for translation, and that any new translation keys exist in the lokalise.com project. (see :doc:`translation documentation <translation>`).
6. Once develop passes, then create a new PR from develop to master.
7. Draft new Release from Github (https://github.com/SEED-platform/seed/releases).
8. Include list of changes since previous release (i.e. the content in the CHANGELOG.md)
9. Verify that the Docker versions are built and pushed to Docker hub (https://hub.docker.com/r/seedplatform/seed/tags/).
10. Go to Read the Docs and enable the latest version to be active (https://readthedocs.org/dashboard/seed-platform/versions/)
