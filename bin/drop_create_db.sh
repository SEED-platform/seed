#!/bin/bash
# drops the ``seed`` DB, then creates it. Add a super_user
# demo@seed.lbl.gov with password demo

dropdb seed
createdb seed
python manage.py syncdb --migrate
python manage.py create_default_user
