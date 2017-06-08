Deployment Guide
================

SEED is intended to be installed on Linux instances in the cloud (e.g. AWS),
and on local hardware. SEED Platform does not officially support Windows for
production deployment. If this is desired, see the Django `notes`_.

.. _notes: https://docs.djangoproject.com/en/1.7/howto/windows/

.. toctree::
    :maxdepth: 2

    aws
    linux

Monitoring
----------

Sentry
^^^^^^

Sentry is used for development. The front end tests are run on Sentry for every commit through
travis.