#!/bin/bash

i=0
files=()
for file in $(find . -path ./venv -prune -o -name '*.feature' | grep -v ".venv")
do
  if [ $(($i % $CIRCLE_NODE_TOTAL)) -eq $CIRCLE_NODE_INDEX ]
  then
    files+=" $file"
  fi
  ((i++))
done

echo "venv/bin/python manage.py harvest ${files[@]} --settings=BE.settings.ci "
venv/bin/python manage.py harvest ${files[@]} --settings=BE.settings.ci
exit $?
