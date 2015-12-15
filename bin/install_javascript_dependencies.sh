#!/usr/bin/env bash
# installs bower dependencies
# assumes npm is installed

echo "installing node dependencies..."
npm install -g bower gulp gulp-load-plugins es6-promise gulp-jshint jshint-stylish gulp-fixmyjs gulp-sourcemaps gulp-sass gulp-autoprefixer gulp-csso
echo ""
echo ""
echo ""
echo "starting bower install"
bower install --config.interactive

if [ ! -f seed/static/vendors/bower_components/fine-uploader/_build/s3.fineuploader.js ];
then
    echo ""
    echo ""
    echo ""
    echo "installing fineuploader dependencies"
    cd seed/static/vendors/bower_components/fine-uploader/
    npm install
    echo ""
    echo ""
    echo ""
    echo ""
    echo "installing grunt-cli..."
    npm install -g grunt-cli
    echo ""
    echo ""
    echo ""
    echo ""
    echo "building fineuploader"
    grunt build
    cd ../../../../../
else
    echo "fineuploader already installed"
fi
