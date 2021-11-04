#!/bin/bash

# Make sure not to echo anything out here becase some of the scripts that test SEED
# call docker-compose run and expect the response to be in the command line.
mkdir -p /seed/collected_static && chmod 775 /seed/collected_static
mkdir -p /seed/media && chmod 777 /seed/media
mkdir -p /seed/media/uploads && chmod 777 /seed/media/uploads
mkdir -p /seed/media/uploads/pm_imports && chmod 777 /seed/media/uploads/pm_imports

# set the owner to uwsgi
chown -R uwsgi /seed/collected_static

exec "$@"
