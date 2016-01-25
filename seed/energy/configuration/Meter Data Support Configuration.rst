Meter Data Support Setup
========================

Add Scheduler Configuration File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Tell SEED to import scheduler module:

.. code-block:: python

    CELERY_IMPORTS=("seed.Meter_data_processor.monthlydataaggregator",
                    "seed.Meter_data_processor.GreenButtonTask")


.. note::


    Under SEED root folder

Set the schedule execution time-interval:

.. code-block:: python

    from datetime import timedelta
    from celery.schedules import crontab
    CELERYD_CONCURRENCY=1
    CELERYBEAT_SCHEDULE = {
        'monthly': {
            'task': 'aggregatemonthlysum',
            'schedule': timedelta(seconds=5), //For testing purpose, should set to timedelta(months=1)
            'args': ()
        },
        'daily': {
            'task': 'doParser',
            'schedule': timedelta(seconds=2), //For testing purpose, should set to timedelta(days=1)
            'args': ()
        },
    }
    CELERY_TIMEZONE = 'America/New_York'


.. note::


    Under SEED root folder

Add Time-Series Database Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Add TS database configuration to config/settings/local_untracked.py

.. code-block:: python

    TSDB = {
        'insert_url': 'http://[your-Kairos-DB-server-address]:8013/api/v1/datapoints',
        'query_url': 'http://[your-Kairos-DB-server-address]:8013/api/v1/datapoints/query',
        'measurement': '[your-measurement-name]'
    }
    LOCAL_TIMEZONE = 'America/New_York'


.. note::
    Kairos use port 8013 as default

Database Updates
^^^^^^^^^^^^^^^^
In SEED, seed/models.py needs to be modified to add/change PostgreSQL tables

Add GreenButton Batch Request Record Tabls:

.. code-block:: python

    class ts_parser_record(models.Model):
        last_ts = models.BigIntegerField()
        url = models.CharField(max_length=500)
        last_date = models.CharField(max_length=50)
        min_date_parameter = models.CharField(max_length=20)
        max_date_parameter = models.CharField(max_length=20)
        building_id = models.CharField(max_length=100)
        active = models.CharField(max_length=10)
        time_type = models.CharField(max_length=50)
        date_pattern = models.CharField(max_length=100)
        sub_id = models.CharField(max_length=200)

        def __str__(self):
            return self.url+', '+str(self.building_id)



If already used ``console$ python manage.py migrate`` to create tables, please create the ``ts_parser_record`` table in PostgreSQL:

.. code-block:: SQL

    CREATE TABLE seed_ts_parser_record(
        last_ts bigint,
        id serial NOT NULL,
        url character varying(500),
        last_date character varying(50),
        min_date_parameter character varying(20),
        max_date_parameter character varying(20),
        building_id character varying(100),
        active character varying(10),
        time_type character varying(50),
        date_pattern character varying(100),
        sub_id character(200),
        CONSTRAINT seed_ts_parser_record_pkey PRIMARY KEY (id)
    )
    WITH (
        OIDS=FALSE
    );
    ALTER TABLE seed_ts_parser_record
        OWNER TO "[your-database-user]";



Update Meter table to create a new column for custom meter id that defined by TS data provider, also create ManyToMany relationship between CanonicalBuilding:

.. code-block:: python

    class Meter(models.Model):
        """Meter specific attributes."""
        name = models.CharField(max_length=100)
        building_snapshot = models.ManyToManyField(
            BuildingSnapshot, related_name='meters', null=True, blank=True
        )
        canonical_building = models.ManyToManyField(
            CanonicalBuilding, related_name='meters', null=True, blank=True
        )
        energy_type = models.IntegerField(max_length=3, choices=ENERGY_TYPES)
        energy_units = models.IntegerField(max_length=3, choices=ENERGY_UNITS)
        custom_meter_id = models.CharField(max_length=100)


