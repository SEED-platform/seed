# This is dumb and hacky but hey, it works
start-stop-daemon --background --start --quiet --pidfile /tmp/flower.pid --exec /usr/local/bin/flower -- --address=127.0.0.1 --auth=".+@buildingenergy.com" --broker=redis://$(python BE/settings/aws/aws.py):6379/1 --port=8080
