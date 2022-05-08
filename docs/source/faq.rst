Frequently Asked Questions
##########################

Here are some frequently asked questions and/or issues.

.. contents::
    :local:
    :depth: 2



Questions
=========
.. _whatisseed:

What is the SEED Platform?
--------------------------

The Standard Energy Efficiency Data (SEED) Platform™ is a web-based application
that helps organizations easily manage data on the energy performance of large
groups of buildings. Users can combine data from multiple sources, clean and
validate it, and share the information with others. The software application
provides an easy, flexible, and cost-effective method to improve the quality
and availability of data to help demonstrate the economic and environmental
benefits of energy efficiency, to implement programs, and to target investment
activity.

The SEED application is written in Python/Django, with AngularJS, Bootstrap,
and other JavaScript libraries used for the front-end. The back-end database
is required to be PostgreSQL.

The SEED web application provides both a browser-based interface for users to
upload and manage their building data, as well as a full set of APIs that app
developers can use to access these same data management functions.

Work on SEED Platform is managed by the National Renewable Energy Laboratory,
with funding from the U.S. Department of Energy.


Issues
======

.. _domain:

Why is the domain set to example.com?
-------------------------------------

If you see example.com in the emails that are sent from your hosted version of SEED then you will
need to update your django sites object in the database.

.. code-block:: bash

    $ ./manage.py shell

    from django.contrib.sites.models import Site
    one = Site.objects.all()[0]
    one.domain = 'newdomain.org'
    one.name = 'SEED'
    one.save()


.. _staticfiles:

Why aren't the static assets being served correctly?
----------------------------------------------------

Make sure that your local_untracked.py file does not have STATICFILES_STORAGE set to anything. If so,
then comment out that section and redeploy/recollect/compress your static assets.
