WORKERS=$(($(nproc) * 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-python manage.py celery worker -B -c $WORKERS --loglevel=INFO -E --maxtasksperchild=1000 -f /home/ubuntu/celery.log
