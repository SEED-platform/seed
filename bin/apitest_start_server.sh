#!/usr/bin/env bash

# starts local server for testing API
echo "migrating"
./manage.py migrate &> tox_migrate.log
echo "creating default user"
./manage.py create_default_user --username=demo@example.com --password=demo123
echo "making SU"
echo "y" | ./manage.py make_superuser --user demo@example.com &> make_supersuer.log
echo "Saving API data"
./manage.py create_test_user_json --username demo@example.com --file ./seed/tests/api/api_test_user.json &> tox_test_user.log
echo "starting celery"
celery -A seed worker -l INFO -c 2 -B --events --maxtasksperchild 1000 & &> celery_log.log
echo "starting server"
./manage.py runserver & &> main.log
sleep 15
echo "exiting start script"
