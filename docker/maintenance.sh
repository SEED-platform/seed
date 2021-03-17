#!/bin/bash

if [ "$1" == 'on' ]
then
  sed -e 's|<small></small>|<small>'"$(date '+%-m/%-d %-H:%M %Z')"'</small>|g' /seed/docker/maintenance.html > /seed/collected_static/maintenance.html
  echo '...maintenance is on...';
elif [ "$1" == 'off' ]
then
  rm -f /seed/collected_static/maintenance.html
  echo '...maintenance is off...';
fi
