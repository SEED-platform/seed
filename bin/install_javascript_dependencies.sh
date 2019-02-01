#!/usr/bin/env bash
# installs npm dependencies
# assumes npm is installed

echo "Installing npm dependencies from package.json"
npm install

echo -e "\n\n\nInstalling UI npm dependencies"
cd vendors
npm install
cd ..
