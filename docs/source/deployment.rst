Deployment Guide
================

SEED is intended to be installed on Linux instances in the cloud (e.g. AWS), and on local hardware. SEED Platform does not officially support Windows for production deployment. If this is desired, see the Django `notes`_.

.. _notes: https://docs.djangoproject.com/en/1.7/howto/windows/

.. toctree::
    :maxdepth: 2

    aws
    linux
    docker
    kubernetes_deployment

Migrations
----------

Migrations are handles through Django; however, various versions have customs actions for the migrations. See the :doc:`migrations page <migrations>` for more information.


Monitoring
----------

Sentry
^^^^^^

Sentry can monitor your webservers for any issues. To enable sentry add the following to
your local_untracked.py files after setting up your Sentry account on sentry.io.

The RAVEN_CONFIG is used for the backend and the SENTRY_JS_DSN is used for the frontend. At the moment,
it is recommended to setup two sentry projects, one for backend and one for frontend.

.. code-block:: python

    import raven

    RAVEN_CONFIG = {
       'dsn': 'https://<user>:<key>@sentry.io/<job_id>',
       # If you are using git, you can also automatically configure the
       # release based on the git info.
       'release': raven.fetch_git_sha(os.path.abspath(os.curdir)),
    }
    SENTRY_JS_DSN = 'https://<key>@sentry.io/<job_id>'
