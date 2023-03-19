#!/usr/bin/env bash
# starts local server and create test user for protractor tests

echo "updating webdriver"
./node_modules/protractor/bin/webdriver-manager update --gecko=false
echo "migrating"
./manage.py migrate &> tox_migrate.log
echo "creating default user"
./manage.py create_default_user --username=demo@example.com --password=demo123
echo "making SU"
echo "y" | ./manage.py make_superuser --user demo@example.com &> make_superuser.log
echo "starting celery"
celery -A seed worker -l INFO -c 2 --max-tasks-per-child 1000 -EBS django_celery_beat.schedulers:DatabaseScheduler &> celery.log &
echo "starting server"
./manage.py runserver & &> main.log
sleep 15
echo "run e2e tests"
./node_modules/protractor/bin/protractor seed/static/seed/tests/protractor-tests/protractorConfigCoverage.js
# echo "install coverall merge stuffs"
# gem install coveralls-lcov
# pip install coveralls-merge
# echo "run lcov to coveralls json"
# coveralls-lcov -v -n protractorReports/lcov.info > coverage.protractor.json
# echo "merge and post coveralls"
# coveralls-merge coverage.protractor.json
