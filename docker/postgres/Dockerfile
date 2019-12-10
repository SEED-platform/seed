FROM seedplatform/postgres-seed:11.2

# Use the old image that has been pushed until we update dependencies!
#ENV POSTGIS_MAJOR 2.5
#ENV POSTGIS_VERSION 2.5.2+dfsg-1~exp1.pgdg90+1
#
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends \
#        postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR=$POSTGIS_VERSION \
#        postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR-scripts=$POSTGIS_VERSION \
#        postgis=$POSTGIS_VERSION \
#        apt-transport-https ca-certificates wget && \
#    rm -rf /var/lib/apt/lists/*
#
#RUN sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/debian/ `lsb_release -c -s` main' > /etc/apt/sources.list.d/timescaledb.list" && \
#    wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | apt-key add - && \
#    apt-get update && \
#    apt-get install -y timescaledb-postgresql-$PG_MAJOR && \
#    apt-get purge -y --auto-remove apt-transport-https ca-certificates wget && \
#    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /docker-entrypoint-initdb.d
COPY ./initdb-postgis.sh /docker-entrypoint-initdb.d/postgis.sh
COPY ./initdb-timescaledb.sh /docker-entrypoint-initdb.d/timescaledb.sh
COPY ./update-postgis.sh /usr/local/bin
