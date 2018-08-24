#!/usr/bin/env bash
# installs npm and bower dependencies
# assumes npm is installed

echo "Installing npm dependencies from packages.json"
npm install
echo -e "\n\n\nInstalling bower dependencies from bower.json"
$(npm bin)/bower install --config.interactive=false --allow-root
