Getting Started
===============

Development Setup
-----------------

.. toctree::
    :maxdepth: 3

   setup_osx


* `git clone git@github.com:seed-platform/seed.git`
* install Postgres 9.3 and redis for cache and message broker
* use a virtualenv if desired
* create a `local_untracked.py` in the `config/settings` folder and add
    CACHE and DB config (example `local_untracked.py.dist`)
* `export DJANGO_SETTINGS_MODULE=config.settings.dev`
* `pip install -r requirements/local.txt`
* `./manage.py syncdb`
* `./manage.py migrate`
* `./manage.py create_default_user`
* `./manage.py runserver`
* `celery -A seed worker -l info -c 4 --maxtasksperchild 1000 --events`
* navigate to `http://127.0.0.1:8000/app/#/profile/admin` in your browser
    to add users to organizations
    * each user must belong to an organization!
* main app runs at `127.0.0.1:8000/app`

The `python manage.py create_default_user` will setup a default `superuser`
which must be used to access the system the first time. The management command
can also create other superusers.

.. code-block:: console

    ./manage.py create_default_user --username=demo2@be.com --organization=be --password=demo123

