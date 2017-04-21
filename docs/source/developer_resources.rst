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

To run flake locally call:

.. code-block:: console

    tox -e flake8

Django Notes
------------

Both Django and AngurlarJS are used for url routing. Django routes are in `seed/urls/main.py`

AWS S3
^^^^^^

Amazon AWS S3 Expires headers should be set on the AngularJS partials if using S3 with the management command:
set_s3_expires_headers_for_angularjs_partials

Example::

    python manage.py set_s3_expires_headers_for_angularjs_partials --verbosity=3

The default user invite reply-to email can be overridden in the config/settings/common.py file. The `SERVER_EMAIL`
settings var is the reply-to email sent along with new account emails.

.. code-block:: console

    # config/settings/common.py
    PASSWORD_RESET_EMAIL = 'reset@seed.lbl.gov'
    SERVER_EMAIL = 'no-reply@seed.lbl.gov'



AngularJS Integration Notes
---------------------------

Template Tags
^^^^^^^^^^^^^

Angular and Django both use `{{` and `}}` as variable delimiters, and thus the AngularJS variable delimiters are
renamed `{$` and `$}`.

.. code-block:: JavaScript

    window.BE.apps.seed = angular.module('BE.seed', ['ngRoute', "ngCookies"], function ($interpolateProvider) {
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

    window.BE.apps.seed.config(['$routeProvider', function ($routeProvider) {
            $routeProvider
                .when('/', {
                    templateUrl: static_url + '/seed/partials/home.html'
                })
                .when('/projects', {
                    controller: 'project_list_controller',
                    templateUrl: static_url + '/seed/partials/projects.html'
                })
                .when('/buildings', {
                    templateUrl: static_url + '/seed/partials/buildings.html'
                })
                .when('/admin', {
                    controller: 'seed_admin_controller',
                    templateUrl: static_url + '/seed/partials/admin.html'
                })
                .otherwise({ redirectTo: '/' });
        }]);

HTML partials in `static/seed/partials/`

on production and staging servers on AWS, or for the partial html templates loaded on S3, or a CDN,
the external resource should be added to the white list in `static/seed/js/seed/js`

.. code-block:: JavaScript

    // white list for s3
    window.BE.apps.seed.config(function( $sceDelegateProvider ) {
    $sceDelegateProvider.resourceUrlWhitelist([
        // localhost
        'self',
        // AWS s3
        'https://be-*.amazonaws.com/**'
        ]);
    });

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

    psql -c 'DROP DATABASE "seeddb"'
    psql -c 'CREATE DATABASE "seeddb" WITH OWNER = "seeduser";'
    psql -c 'GRANT ALL PRIVILEGES ON DATABASE "seeddb" TO seeduser;'
    psql -c 'ALTER USER seeduser CREATEDB;'

    psql -c 'ALTER USER seeduser CREATEROLE;'
    ./manage.py migrate
    ./manage.py create_default_user \
        --username=testuser@seed.org \
        --password=password \
        --organization=testorg

Testing
-------

JS tests can be run with Jasmine at the url `app/angular_js_tests/`.

Python unit tests are run with

.. code-block:: console

    python manage.py test --settings=config.settings.test

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

