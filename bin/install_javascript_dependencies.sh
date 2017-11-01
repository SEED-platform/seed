#!/usr/bin/env bash
# installs npm dependencies, bower dependencies, and builds fine-uploader
# assumes npm is installed

echo "Installing npm dependencies from packages.json"
npm install
echo -e "\n\n\nInstalling bower dependencies from bower.json"
$(npm bin)/bower install --config.interactive=false --allow-root

if [ ! -f seed/static/vendors/bower_components/fine-uploader/_build/s3.fineuploader.js ];
then
    grunt=$(npm bin)/grunt
    cd seed/static/vendors/bower_components/fine-uploader/
    echo -e "\n\n\nBuilding fineuploader"
    # Fix uglification error
    sed -i -e 's/compress: true/compress: \{\}/g' Gruntfile.coffee
    npm install
    $grunt build
    rm -rf node_modules
    cd ../../../../../
else
    echo -e "\n\n\nFineuploader already built"
fi
