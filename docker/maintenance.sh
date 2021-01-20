#!/bin/bash

if [ "$1" == 'on' ]
then
  cp /seed/docker/maintenance.html /seed/collected_static
  echo '...maintenance is on...';
elif [ "$1" == 'off' ]
then
  rm -f /seed/collected_static/maintenance.html
  echo '...maintenance is off...';
fi
