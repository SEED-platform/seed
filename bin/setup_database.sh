#!/bin/bash
cd /seed

source ./bin/docker_environment.sh
./manage.py syncdb
./manage.py migrate
./manage.py create_default_user
