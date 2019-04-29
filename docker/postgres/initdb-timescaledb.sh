#!/bin/sh

set -e

timescaledb-tune -conf-path /var/lib/postgresql/data/postgresql.conf -quiet -yes
service postgresql restart
