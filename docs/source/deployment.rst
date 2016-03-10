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

Flower
^^^^^^

Flower is used to monitor background tasks. Assuming your redis broker is
running on `localhost` and on port `6379`, DB `1`. Then go to localhost:5555
to check celery. If running on AWS, the `bin/start_flower.sh` will start
flower on port `8080` and be available for Google credentialed accounts.

.. code-block:: console

    flower --port=5555 --broker=redis://localhost:6379/1`


Sentry
^^^^^^
.. todo:: Fill this out