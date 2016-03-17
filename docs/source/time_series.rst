Time Series Data Integration
============================

The SEED Platform can handle interval meter data (i.e. data reported less than
monthly) by the use of KairosDB.


Django Configuration
--------------------

Add Scheduler Configuration File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The common.py includes the default backend tasks needed for pulling
the Green Button data on a daily interval, and to aggregate the monthly data.

.. code-block:: python

    CELERY_IMPORTS = ('seed.energy.meter_data_processor.tasks')
    CELERYBEAT_SCHEDULE = {
        'Run monthly': {
            'task': 'seed.energy.meter_data_processor.tasks.aggregate_monthly_data',
            'schedule': timedelta(weeks=4),
            'args': ()
        },
        'Run daily': {
            'task': 'seed.energy.meter_data_processor.tasks.green_button_task_runner',
            'schedule': timedelta(days=1),
            'args': ()
        },
    }

    CELERY_IMPORTS=(
        "seed.Meter_data_processor.monthlydataaggregator",
        "seed.Meter_data_processor.GreenButtonTask"
    )
    CELERY_TIMEZONE = 'America/New_York'


The time series database is KairosDB (see instructions below on installation).
The config file will need to be configured to point to the running instance
of KairosDB. For example:

.. code-block:: python

    TSDB = {
        'insert_url': 'http://[your-Kairos-DB-server-address]:8013/api/v1/datapoints',
        'query_url': 'http://[your-Kairos-DB-server-address]:8013/api/v1/datapoints/query',
        'measurement': '[your-measurement-name]'
    }
    LOCAL_TIMEZONE = 'America/New_York'



Add Time-Series Database Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Add TS database configuration to config/settings/local_untracked.py




.. note::
    Kairos use port 8013 as default

Database Updates
^^^^^^^^^^^^^^^^

Run migrations to add the `meters` and various tracking tables to the database

.. code-block:: console

    ./manage.py migrate


KairosDB
--------

Prerequisites
^^^^^^^^^^^^^

Prerequisites for Kairos:

* Java 1.6 or later
* Database: We are using Cassandra as datastore


Install Cassandra
^^^^^^^^^^^^^^^^^

* Install the Oracle Java Virtual Machine

.. note::

    Cassandra requires that the Oracle Java SE Runtime Environment (JRE) be
    installed. This step, we install and verify that it's the default JRE.

    Verify JRE is running the command below and making sure that the version is
    1.8.0.

    .. code-block:: console

        java –version

    If the Java version is old, then try adding a new repo using

    .. code-block:: console

        sudo add-apt-repository ppa:webupd8team/java
        sudo apt-get update
        sudo apt-get install oracle-java8-set-default


    Set JAVA_HOME in /etc/environment (something like as shown below)

    .. code-block:: console

        JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64/bin/java"


* Install Cassandra

    .. code-block:: console

        cd /etc/apt

        # add the following repos to apt.list -- Note: 23x if version 2.3
        deb http://www.apache.org/dist/cassandra/debian 22x main
        deb-src http://www.apache.org/dist/cassandra/debian 22x main

        gpg --keyserver pgp.mit.edu --recv-keys F758CE318D77295D
        gpg --export --armor F758CE318D77295D | sudo apt-key add –
        gpg --keyserver pgp.mit.edu --recv-keys 2B5C1B00
        gpg --export --armor 2B5C1B00 | sudo apt-key add –
        gpg --keyserver pgp.mit.edu --recv-keys 0353B12C
        gpg --export --armor 0353B12C | sudo apt-key add –

        apt-get update
        apt-get install Cassandra

        cd /etc/Cassandra

        # Verify configuration in: /etc/Cassandra/cassandra.yaml
        service Cassandra start

        service Cassandra status

* Install KairosDB

    Visit KairosDB site: https://github.com/kairosdb/kairosdb/releases/

    .. code-block:: console

        wget https://github.com/kairosdb/kairosdb/releases/download/v1.1.1/kairosdb-1.1.1-1.tar.gz
        tar –xzf kairosdb-1.1.1-1.tar.gz

        cd kairosdb/conf

        # Set datastore in configuration file:
        nano kairosdb.properties

    In the file comment the line where H2 is set as datastore and uncomment
    Cassandra module. So the file should look like this.

    #kairosdb.service.datastore=org.kairosdb.datastore.h2.H2Module
    kairosdb.service.datastore=org.kairosdb.datastore.cassandra.CassandraModule

    .. note::

        KairosDB runs on Port 8013. So if any other service is running on the
        port, configure service on a different port say 4244

    .. code-block:: console

        cd ../bin/
        ./kairosdb.sh run
        ps ax | grep kairosdb


