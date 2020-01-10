## Standard Energy Efficiency Data (SEED) Platform™
[![Build Status][travis-img]][travis-url] [![Coverage Status][coveralls-img]][coveralls-url]
[![](http://readthedocs.org/projects/seed-platform/badge/?version=stable)](http://seed-platform.readthedocs.io/en/stable/)
[![](http://readthedocs.org/projects/seed-platform/badge/?version=latest)](http://seed-platform.readthedocs.io/en/latest/)

The SEED Platform is a web-based application that helps organizations easily
manage data on the energy performance of large groups of buildings. Users can
combine data from multiple sources, clean and validate it, and share the
information with others. The software application provides an easy, flexible,
and cost-effective method to improve the quality and availability of data to
help demonstrate the economic and environmental benefits of energy efficiency,
to implement programs, and to target investment activity.

The SEED application is written in Python/Django, with AngularJS, Bootstrap,
and other javascript libraries used for the front-end. The back-end database
is required to be PostgreSQL.

The SEED web application provides both a browser-based interface for users to
upload and manage their building data, as well as a full set of APIs that app
developers can use to access these same data management functions.  From a
running server, the Swagger API documentation can be found at `/api/swagger`
or from the front end by clicking the API documentation link in the sidebar.


### Installation

* Production on Amazon Web Service: See [Installation Notes][production-aws-url]
* Development on Mac OSX: [Installation Notes][development-mac-osx]
* Development using Docker: [Installation Notes][development-docker]

### Starting SEED Platform

In production the following two commands will run the web server (uWSGI) and
the background task manager (Celery) with:

```
bin/start_uwsgi.sh
bin/start_celery.sh
```

In development mode, you can start the web server (uWSGI) and the background
task manager (Celery) with:

```
./manage.py runserver
celery -A seed worker -l info -c 4 --maxtasksperchild 1000 --events
```

### Developer Resources

* Several notes regarding Django and AngularJS integration: See [Developer Resources][developer-resources]

#### Testing

* Running tests: See [Testing Notes][developer-testing-notes]

### Copyright
Copyright ©  2014 - 2020, The Regents of the University of California, through
Lawrence Berkeley National Laboratory (subject to receipt of any required
approvals from the U.S. Department of Energy) and contributors. All rights
reserved.


[development-docker]: https://github.com/SEED-platform/seed/blob/develop/docs/source/setup_docker.rst
[development-mac-osx]: https://github.com/SEED-platform/seed/blob/develop/docs/source/setup_osx.rst
[production-aws-url]: http://www.github.com/seed-platform/seed/wiki/Installation
[developer-resources]: https://github.com/SEED-platform/seed/blob/develop/docs/source/developer_resources.rst
[developer-testing-notes]: https://github.com/SEED-platform/seed/blob/39bc55b846f0c1dc4c8d1574272cac50378de651/docs/source/developer_resources.rst#testing
[read-the-docs-stable]: http://seed-platform.readthedocs.io/en/stable
[read-the-docs-stable-img]: https://readthedocs.io/projects/seed-platform/badge/?version=stable
[read-the-docs-latest]: http://seed-platform.readthedocs.io/en/latest/
[read-the-docs-latest-img]: https://readthedocs.io/projects/seed-platform/badge/?version=latest
[travis-img]: https://travis-ci.org/SEED-platform/seed.svg?branch=develop
[travis-url]: https://travis-ci.org/SEED-platform/seed
[coveralls-img]: https://coveralls.io/repos/github/SEED-platform/seed/badge.svg?branch=HEAD
[coveralls-url]: https://coveralls.io/github/SEED-platform/seed?branch=HEAD
