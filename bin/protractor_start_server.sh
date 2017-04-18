#!/usr/bin/env bash
# starts local server and create test user for protractor tests

echo "updating webdriver"
./node_modules/protractor/bin/webdriver-manager update
echo "migrating"
./manage.py migrate &> tox_migrate.log
echo "creating default user"
./manage.py create_default_user --username=demo@example.com --password=demo123
echo "making SU"
echo "y" | ./manage.py make_superuser --user demo@example.com &> make_superuser.log
echo "starting celery"
celery -A seed worker -l INFO -c 2 -B --events --maxtasksperchild 1000 & &> celery.log
echo "starting server"
./manage.py runserver & &> main.log
sleep 15
echo "run e2e tests"
npm test
