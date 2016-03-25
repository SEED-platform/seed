#!/usr/bin/env bash
# installs npm and bower dependencies
# assumes npm is installed

echo -e "Installing global dependencies..."
if ! npm list -g bower; then
    sudo npm install -g bower
fi
if ! npm list -g grunt-cli; then
    sudo npm install -g grunt-cli
fi
if ! npm list -g gulp-cli; then
    sudo npm install -g gulp-cli
fi
echo -e "\n\n\nInstalling npm dependencies..."
npm install
echo -e "\n\n\nInstalling bower dependencies"
bower install --config.interactive=false

if [ ! -f seed/static/vendors/bower_components/fine-uploader/_build/s3.fineuploader.js ];
then
    echo -e "\n\n\nInstalling fineuploader dependencies"
    cd seed/static/vendors/bower_components/fine-uploader/
    npm install
    echo "\n\n\nBuilding fineuploader"
    grunt build
    cd ../../../../../
else
    echo -e "\n\n\nFineuploader already installed"
fi
