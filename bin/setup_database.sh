#!/bin/bash

# NL (1/29/2016) -- Can we delete this file, it seemed to be for docker
cd /seed

./manage.py syncdb
./manage.py migrate
./manage.py create_default_user
