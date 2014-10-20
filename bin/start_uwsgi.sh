WORKERS=$(($(nproc) / 2))
WORKERS=$(($WORKERS>1?$WORKERS:1))
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program /usr/local/bin/uwsgi --http 127.0.0.1:8000 --module wsgi --daemonize /home/ubuntu/uwsgi.log --max-requests 5000 --pidfile /tmp/uwsgi.pid --cheaper-initial 1 -p $WORKERS --single-interpreter --enable-threads --touch-reload /home/ubuntu/touch-reload
