#!/usr/bin/env bash
# installs npm dependencies, bower dependencies, and builds fine-uploader
# assumes npm is installed

echo "Installing npm dependencies..."
npm install
echo -e "\n\n\nInstalling bower dependencies"
npm run bower install --config.interactive=false

if [ ! -f seed/static/vendors/bower_components/fine-uploader/_build/s3.fineuploader.js ];
then
    echo -e "\n\n\nBuilding fineuploader"
    # Fix uglification error
    sed -ie 's/compress: true/compress: \{\}/g' seed/static/vendors/bower_components/fine-uploader/Gruntfile.coffee
    grunt=$(npm bin)/grunt
    (cd seed/static/vendors/bower_components/fine-uploader/ && npm install && $grunt build)
else
    echo -e "\n\n\nFineuploader already installed"
fi
