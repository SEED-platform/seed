Upgrade a SEED database from Postgres 12 to Postgres 18
=======================================================

Assumptions
-----------

- This process assumes that the source database is Postgres 12.7 with TimescaleDB 2.3.0 from ``timescale/timescaledb-postgis:2.3.0-pg12`` or ``timescale/timescaledb-postgis:latest-pg12``
- This also assumes that you have a directory in the host filesystem, e.g. ``~/share``, that is bind mounted to ``/share`` in your existing database container

1. Create a dump of the current database

.. code-block:: bash

   docker exec seed_postgres pg_dump -d seed -U seeduser -Fc -f /share/seed-pg12-ts2.3.0.dump

2. Create a temporary Postgres 13 container using the Docker image ``timescale/timescaledb-ha:pg13.22-ts2.15.3-oss``

.. code-block:: bash

   docker run --rm --name=seed-pg13 -e POSTGRES_DB=seed -e POSTGRES_USER=seeduser -e POSTGRES_PASSWORD=password -v ~/share:/share timescale/timescaledb-ha:pg13.22-ts2.15.3-oss

Once the container has finished initializing, open a separate shell

.. code-block:: bash

   docker exec -it seed-pg13 bash
   psql -d seed -U seeduser -c "CREATE EXTENSION postgis;"
   psql -d seed -U seeduser -c "DROP EXTENSION timescaledb;"
   psql -d seed -U seeduser -c "CREATE EXTENSION timescaledb WITH VERSION '2.3.0';"
   psql -d seed -U seeduser -c "SELECT timescaledb_pre_restore();"
   pg_restore -d seed -U seeduser /share/seed-pg12-ts2.3.0.dump
   psql -d seed -U seeduser -c "SELECT timescaledb_post_restore();"
   psql -d seed -U seeduser -c "ALTER EXTENSION timescaledb UPDATE;"
   pg_dump -d seed -U seeduser -Fc -f /share/seed-pg13-ts2.15.3.dump

3. Create a temporary Postgres 16 container using the Docker image ``timescale/timescaledb-ha:pg16.13-ts2.26.4-oss``

.. code-block:: bash

   docker run --rm --name=seed-pg16 -e POSTGRES_DB=seed -e POSTGRES_USER=seeduser -e POSTGRES_PASSWORD=password -v ~/share:/share timescale/timescaledb-ha:pg16.13-ts2.26.4-oss

Once the container has finished initializing, open a separate shell

.. code-block:: bash

   docker exec -it seed-pg16 bash
   psql -d seed -U seeduser -c "CREATE EXTENSION postgis;"
   psql -d seed -U seeduser -c "DROP EXTENSION timescaledb;"
   psql -d seed -U seeduser -c "CREATE EXTENSION timescaledb WITH VERSION '2.15.3';"
   psql -d seed -U seeduser -c "SELECT timescaledb_pre_restore();"
   pg_restore -d seed -U seeduser /share/seed-pg13-ts2.15.3.dump
   psql -d seed -U seeduser -c "SELECT timescaledb_post_restore();"
   psql -d seed -U seeduser -c "ALTER EXTENSION timescaledb UPDATE;"
   pg_dump -d seed -U seeduser -Fc --compress=zstd:6 -f /share/seed-pg16-ts2.26.4.dump

4. Start the new, permanent Postgres 18 container using the Docker image ``timescale/timescaledb-ha:pg18.3-ts2.26.4-oss``

.. code-block:: bash

   docker run -d --name=seed-pg18 -e POSTGRES_DB=seed -e POSTGRES_USER=seeduser -e POSTGRES_PASSWORD=password -v ~/share:/share timescale/timescaledb-ha:pg18.3-ts2.26.4-oss

Once the container has finished initializing, open a separate shell

.. code-block:: bash

   docker exec -it seed-pg18 bash
   psql -d seed -U seeduser -c "CREATE EXTENSION postgis;"
   psql -d seed -U seeduser -c "SELECT timescaledb_pre_restore();"
   pg_restore -d seed -U seeduser /share/seed-pg16-ts2.26.4.dump
   psql -d seed -U seeduser -c "SELECT timescaledb_post_restore();"
   pg_dump -d seed -U seeduser -Fc --compress=zstd:6 -f /share/seed-pg18.dump
