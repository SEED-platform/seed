
## Standard Energy Efficiency Data (SEED)


See [AWS.setup.rst](docs/source/AWS.setup.rst) for the Amazon Web Services setup guide.

Both Django and AngurlarJS used for url routing.
Angular and Django both use `{{` and `}}` as variable delimiters, and thus the angular variable delimiters are renamed `{$` and `$}`.

### Django notes
routes in `SEED/urls/py`

Amazon AWS S3 Expires headers should be set on the AngularJS partials if using S3 with the management command: set_s3_expires_headers_for_angularjs_partials
 usage: `python manage.py set_s3_expires_headers_for_angularjs_partials --verbosity=3`

The default user invite reply-to email can be overridden in the BE/settings/common.py file. The `SERVER_EMAIL` settings var is the reply-to email sent along with new account emails.

```python
# BE/settings/common.py
PASSWORD_RESET_EMAIL = 'reset@buildingenergy.com'
SERVER_EMAIL = 'no-reply@buildingenergy.com'
```

### AngularJS notes
#### template tags
For compatibility in partials with Django template tags (i.e. `{{` and `}}`), we renamed AngularJS variable delimiters or curly braces to `{$` and `$}`.

```
window.BE.apps.seed = angular.module('BE.seed', ['ngRoute', "ngCookies"], function ($interpolateProvider) {
        $interpolateProvider.startSymbol("{$");
        $interpolateProvider.endSymbol("$}");
    }
);
```

#### Django CSFR token and AJAX requests
For ease of making angular `$http` requests, we automatically add the CSFR token to all `$http` requests as recommended by http://django-angular.readthedocs.org/en/latest/integration.html#xmlhttprequest

```
window.BE.apps.seed.run(function ($http, $cookies) {
    $http.defaults.headers.common['X-CSRFToken'] = $cookies['csrftoken'];
});
```

#### routes and partials or views
routes in `static/seed/js/seed.js` (the normal angularjs `app.js`)

```
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
```
html partials in `static/seed/partials/`

on production and staging servers on AWS, or for the partial html templates loaded on S3, or a CDN, the external resource should be added to the white list in `static/seed/js/seed/js`

```
// white list for s3
window.BE.apps.seed.config(function( $sceDelegateProvider ) {
$sceDelegateProvider.resourceUrlWhitelist([
    // localhost
    'self',
    // AWS s3
    'https://be-*.amazonaws.com/**'
    ]);
});
```

#### tests
JS tests can be run with Jasmine at the url `app/angular_js_tests/`

`python manage.py test` will run the python unit tests, we also use coverage
to check the ammount of SLOC covered under tests. The coverage config is
in [.coveragerc](.coveragerc)

```console
$ coverage run manage.py test --settings=BE.settings.ci
$ coverage report --fail-under=83
```

`flake8` will run the PEP8 compliance tests. Its config is in [tox.ini](tox.ini)

```console
$ flake8
```

`jshint` will run the JS compliance tests. The jshint config is in [.jshintrc](.jshintrc)

```console
$ jshint seed/static/seed/js
```

### running
The following two commands will run uwsgi and celeryd.

```
bin/start_uwsgi.sh
bin/start_celery.sh
```

In dev mode, you can start the Django dev server and celery:

```
./manage.py runserver
./manage.py celeryd -c 4 --loglevel=INFO -E --maxtasksperchild=1000
```

#### flower
monitor background tasks `flower --port=5555 --broker=redis://localhost:6379/1`
assuming your redis broker is running on `localhost` and on port `6379`, DB `1`. Then goto localhost:5555 to check celery.
If running on AWS, the `bin/start_flower.sh` will start flower on port `8080` and be available for google credentialed buildingenergy.com accounts.


### dev setup:
* `git clone git@github.com:buildingenergy/seed.git`
* install Postgres 9.3 and redis for cache and message broker
* use a virtualenv if desired
* create a `local_untracked.py` in the `BE/settings` folder and add CACHE and DB config (example `local_untracked.py.dist`)
* `export DJANGO_SETTINGS_MODULE=BE.settings.dev`
* `pip install -r requirements.txt`
* `./manage.py syncdb`
* `./manage.py migrate`
* `./manage.py create_default_user`
* `./manage.py runserver`
* `./manage.py celeryd`
* navaigate to `http://127.0.0.1:8000/app/#/profile/admin` in your browser to add users to organizations
    * each user must belong to an organization!
* main app runs at `127.0.0.1:8000/app`

The `python manage.py create_default_user` will setup a default `superuser`
which must be used to access the system the first time. The management command
can also create other superusers.

```console
./manage.py create_default_user --username=demo2@be.com --organization=be --password=demo123
```

### Copyright:
Copyright ©  2014 Building Energy Inc.

### Logs :
Information about  error logging can be found here - https://docs.djangoproject.com/en/1.7/topics/logging/

Below is a standard set of error messages from Django.

A logger is configured to have a log level. This log level describes the severity of the messages that the logger will handle. Python defines the following log levels:

    DEBUG: Low level system information for debugging purposes
    INFO: General system information
    WARNING: Information describing a minor problem that has occurred.
    ERROR: Information describing a major problem that has occurred.
    CRITICAL: Information describing a critical problem that has occurred.

Each message that is written to the logger is a Log Record. The log record is stored in the webserver & Celery
