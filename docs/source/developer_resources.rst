Developer Resources
===================

.. toctree::

    migrations
    translation


General Notes
-------------

Pre-commit
^^^^^^^^^^
We use precommit commits for formatting. Set it up locally with
```
pre-commit install
```

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

.. code-block:: bash

    tox -e flake8

Python Type Hints
^^^^^^^^^^^^^^^^^

Python type hints are beginning to be added to the SEED codebase. The benefits are
eliminating some accidental typing mistakes to prevent bugs as well as a better IDE
experience.

Usage
*****

SEED does not require exhaustive type annotations, but it is recommended you add them if you
create any new functions or refactor any existing code where it might be beneficial
and not require a ton of additional effort.

When applicable, we recommend you use `built-in collection types <https://docs.python.org/3/whatsnew/3.9.html#type-hinting-generics-in-standard-collections>`_
such as :code:`list`, :code:`dict` or :code:`tuple` instead of the capitalized types
from the :code:`typing` module.

Common gotchas:
- If trying to annotate a class method with the class itself, import :code:`from __future__ import annotations`
- If you're getting warnings about runtime errors due to a type name, make sure your IDE is set up to point to an environment with python 3.9
- If you're wasting time trying to please the type checker, feel free to throw :code:`# type: ignore` on the problematic line (or at the top of the file to ignore all issues for that file)

Type Checking
*************

CI currently runs static type checking on the codebase using `mypy <http://mypy-lang.org/>`_. For
your own IDE, we recommend the following extensions:

- VSCode: `Pylance <https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance>`_ (uses Microsoft's Pyright type checking)

To run the same typechecking applied in CI (i.e., using mypy) you can run the following

.. code-block:: bash

    tox -e mypy


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
                    'column_description': 'Geocoding Confidence',
                    'data_type': 'number',
                }, {
                    'column_name': 'geocoding_confidence',
                    'table_name': 'TaxLotState',
                    'display_name': 'Geocoding Confidence',
                    'column_description': 'Geocoding Confidence',
                    'data_type': 'number',
                }
            ]

            # Go through all the organizations
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
                        # If the column exists, then update the display_name and data_type if empty
                        c = columns.first()
                        if c.display_name is None or c.display_name == '':
                            c.display_name = new_db_field['display_name']
                        if c.data_type is None or c.data_type == '' or c.data_type == 'None':
                            c.data_type = new_db_field['data_type']
                                for col in columns:
                        # If the column exists, then update the column_description if empty
                        if c.column_description is None or c.column_description == '':
                            c.column_description = new_db_field['column_description']
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


NginX Notes
-----------

Toggle *maintenance mode* to display a maintenance page and prevent access to all site resources including API endpoints:

.. code-block:: bash

    docker exec seed_web ./docker/maintenance.sh on
    docker exec seed_web ./docker/maintenance.sh off


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

.. code-block:: bash

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

.. code-block:: bash

    createuser -U seed seeduser

    psql -c 'DROP DATABASE "seed"'
    psql -c 'CREATE DATABASE "seed" WITH OWNER = "seeduser";'
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seed" TO seeduser;'
    psql -c 'ALTER USER "seeduser" CREATEDB CREATEROLE SUPERUSER;'
    psql -d seed -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
    psql -d seed -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'
    psql -d seed -c 'SELECT timescaledb_pre_restore();'
    psql -d seed -c 'SELECT timescaledb_post_restore();'

    ./manage.py migrate
    ./manage.py create_default_user \
        --username=demo@seed-platform.org \
        --password=password \
        --organization=testorg

Restoring a Database Dump
-------------------------

.. code-block:: bash

    psql -c 'DROP DATABASE "seed";'
    psql -c 'CREATE DATABASE "seed" WITH OWNER = "seeduser";'
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seed" TO "seeduser";'
    psql -c 'ALTER USER "seeduser" CREATEDB CREATEROLE SUPERUSER;'
    psql -d seed -c 'CREATE EXTENSION IF NOT EXISTS postgis;'
    psql -d seed -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'
    psql -d seed -c 'SELECT timescaledb_pre_restore();'

    # restore a previous database dump (must be pg_restore 12+)
    /usr/lib/postgresql/12/bin/pg_restore -U seeduser -d seed /backups/prod-backups/prod_20191203_000002.dump
    # if any errors appear during the pg_restore process check that the `installed_version` of the timescaledb extension where the database was dumped matches the extension version where it's being restored
    # `SELECT default_version, installed_version FROM pg_available_extensions WHERE name = 'timescaledb';`

    psql -d seed -c 'SELECT timescaledb_post_restore();'

    ./manage.py migrate

    # if needed add a user to the database
    ./manage.py create_default_user \
        --username=demo@seed-platform.org \
        --password=password \
        --organization=testorg


    # if restoring a production backup to a different deployment update the site settings for password reset emails
    ./manage.py shell

    from django.contrib.sites.models import Site
    site = Site.objects.first()
    site.domain = 'dev1.seed-platform.org'
    site.name = 'SEED Dev1'
    site.save()


Migrating the Database
----------------------

Migrations are handles through Django; however, various versions have customs actions for the migrations. See the :doc:`migrations page <migrations>` for more information based on the version of SEED.


Testing
-------

JS tests can be run with Jasmine at the url `/angular_js_tests/`.

Python unit tests are run with

.. code-block:: bash

    python manage.py test --settings=config.settings.test

Note on geocode-related testing:
    Most of these tests use VCR.py and cassettes to capture and reuse recordings of HTTP requests and responses. Given that, unless you want to make changes and/or refresh the cassettes/recordings, there isn't anything needed to run the geocode tests.

    In the case that the geocoding logic/code is changed or you'd like to the verify the MapQuest API is still working as expected, you'll need to run the tests with a small change. Namely, you'll want to provide the tests with an API key via an environment variable called "TESTING_MAPQUEST_API_KEY" or within your local_untracked.py file with that same variable name.

    In order to refresh the actual cassettes, you'll just need to delete or move the old ones which can be found at ".seed/tests/data/vcr_cassettes". The API key should be hidden within the cassettes, so these new cassettes can and should be pushed to GitHub.

Run coverage using

.. code-block:: bash

    coverage run manage.py test --settings=config.settings.test
    coverage report --fail-under=83

Python compliance uses PEP8 with flake8

.. code-block:: bash

    flake8
    # or
    tox -e flake8

JS Compliance uses jshint

.. code-block:: bash

    jshint seed/static/seed/js

Building Documentation
----------------------

Older versions of the source code documentation are (still) on readthedocs; however, newer versions are built and pushed to the seed-website repository manually. To build the documentation follow the script below:

.. code-block:: bash

        cd docs
        rm -rf htmlout
        sphinx-build -b html source htmlout

For releasing, copy the ``htmlout`` directory into the seed-platform's website repository under ``docs/code_documentation/<new_version>``. Make sure to add the new documentation to the table in the ``docs/developer_resources.md``.

Contribution Instructions / Best Practices
------------------------------------------

If this is the first time contributing and you are outside of the DOE National Lab system, then you will need to review and fill out the contribution agreement which is found in `SEED's Contribution Agreement in the GitHub repository`_

The desired workflow for development and submitting changes is the following:

#. Fork the repository on GitHub if you do not have access to the repository, otherwise, work within the https://github.com/seed-platform/seed repository.
#. Ensure there is a ticket/issue created for the work you are doing. Verify that the ticket is assigned to you and that it is part of the latest project board on the GitHub site (https://github.com/orgs/SEED-platform/projects).
#. Move the ticket/issue to 'In Progress' in the GitHub project tracker when you begin work
#. Create a branch off of develop (unless it is a hotfix, then branch of the appropriate tag). The recommended naming convention is <issue_id>-short-descriptive-name.
#. Make changes and write a test for the code added.
#. Make sure tests pass locally. Most branches created and pushed to GitHub will be tested automatically.
#. Upon completion of the work, create a pull request (PR) against the develop branch (or hotfix branch if applicable). In the PR description fill out the requested information and include the issue number (e.g., #1234).
#. Assign one label to the PR (not the ticket/issue) in order to auto-populate change logs (e.g., Bug, Feature, Maintenance, Performance, DoNotPublish) This is required and CI will fail if not present.
    * **Bug** (these will appear as "Bug Fixes" in the change log)
    * **Feature** (features will appear as “New Features” item in the change log)
    * **Enhancement** (these will appear as “Improvements" in the change log)
    * **Maintenance** (these will appear under “Maintenance" in the change log)
    * **Performance** (these will appear under “Maintenance" in the change log)
    * **Documentation** (these will appear under “Maintenance" in the change log)
    * **Do not publish** (these will no appear in the change log)
#. Ensure all tests pass.
#. Assign a reviewer to the PR.
#. If the reviewer requests changes, then addresses changes and re-assign the reviewer as needed.
#. Once approved, merge the PR!
#. Move the related ticket(s)/issue(s) to the 'Ready to Deploy' column in the GitHub project tracker.

Release Instructions
--------------------

To make a release do the following:

#. Create a branch to prepare the updates (e.g., 2.16.0-release-prep).
#. Github admin user, on develop branch: update the ``package.json`` and ``npm-shrinkwrap.json`` files with the most recent version number. Always use MAJOR.MINOR.RELEASE.
#. Update the ``docs/sources/migrations.rst`` file with any required actions.
#. Push updates to new branch on GitHub, then go to the releases page to draft a new release which will generate the changelog.
#. Copy the GitHub change log results into the CHANGELOG.md. Cleanup the formatting and items as needed (make sure the spelling is correct, starts with a capital letter, etc.)
#. Make sure that any new UI needing localization has been tagged for translation, and that any new translation keys exist in the lokalise.com project. (see :doc:`translation documentation <translation>`).
#. Create PR for release preparation and merge after tests/reviews pass.
#. Once develop tests pass, then create a new PR from develop to main.
#. Draft new Release from Github (https://github.com/SEED-platform/seed/releases).
#. Include list of changes since previous release (i.e., the content in the CHANGELOG.md)
#. Verify that the Docker versions are built and pushed to Docker hub (https://hub.docker.com/r/seedplatform/seed/tags/).
#. Publish the new documentation in the seed-platform website repository (see instructions above under Building Documentation).

.. _`SEED's Contribution Agreement in the GitHub repository`: https://github.com/SEED-platform/seed/blob/develop/.github/CONTRIBUTING.md
