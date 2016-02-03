/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * directive sd-uploader: wraps fineuploader.js assumed AWS creds are in global
 *                        namespace: window.config.AWS_UPLOAD_BUCKET_NAME window.config.AWS_CLIENT_ACCESS_KEY
 *   buttontext: string - text for the button
 *   sourcetype: string - upon upload successful, send the sourcetype param to 
 *                        the server to store the linked file
 *   eventfunc: callback function with three arguments: `message`, `filename`, `progress`
 *              `message` - string - options: "upload_submitted",
 *              "upload_in_progress", "upload_complete", and "invalid_extension"
 *              `filename` - string name of the file uploaded
 *              `progress` - JS object with keys `loaded` and `total` where
 *                           `loaded` / `total` * 100.0 is the percent uploaded
 *  importrecord - int or string - id of import record or dataset
 *  
 */
var UPLOADER_ALLOWED_EXTENSIONS = ['csv', 'xls', 'xlsx', 'xml'];

var makeS3Uploader = function(scope, element, attrs, filename) {
    var uploader = new qq.s3.FineUploader({
    element: element[0],
    request: {
        endpoint: document.location.protocol + '//' + window.BE.AWS_UPLOAD_BUCKET_NAME + '.s3.amazonaws.com',
        accessKey: window.BE.AWS_CLIENT_ACCESS_KEY,
        params: {category: 'data_imports'}
    },
    validation: {
        allowedExtensions: UPLOADER_ALLOWED_EXTENSIONS
    },
    /**
     * showMessage: callback override for error messages, e.g. 
     * "upload failed", "file too large", etc. This checks to see if the 
     * invalid extension message is the message, and uses the directive's 
     * callback in place of `window.alert` (which in turn uses a bootstrap
     * alert).
     */
    showMessage: function(message){
        var invalid_extension = "invalid extension. Valid extension(s):";
        if (message.indexOf(invalid_extension) > -1) {
            scope.eventfunc({message: "invalid_extension"});
        } else {
            window.alert(message);
        }
    },
    text: {
        uploadButton: scope.buttontext
    },
    retry: {
        enableAuto: true
    },
    signature: {
        endpoint: window.BE.urls.uploader_signature_endpoint,
        customHeaders: {
            'X-CSRFToken': BE.csrftoken
         }
    },
    /**
     * uploadSuccess: makes a POST to `data/s3_upload_complete` with the 
     * params. `source_type` is set as an HTML element attribute and should
     * semantically define the source type of the file. In the case of 
     * SEED: a Portfolio Manager file or a covered assessor buildings file
     */
    uploadSuccess: {
        endpoint: window.BE.urls.uploader_success_endpoint,
        params: {
            'csrfmiddlewaretoken': BE.csrftoken,
            'import_record': scope.importrecord,
            'source_type': scope.sourcetype,
            'source_program': scope.sourceprog,
            'source_program_version': scope.sourcever
        }
    },
    iframeSupport: {
        localBlankPathPage: '/success.html'
    },
    /**
     * objectProperties: sets the filename to be stored in the S3 bucket
     * i.e. the JS timestamp is appended to the uploaded filename
     */
    objectProperties: {
        key: function(fileId) {
                 var filename = encodeURIComponent(uploader.getName(fileId));
                 var timestamp = Math.round(new Date().getTime() / 1000);
                 return "data_imports/" + filename + "." + timestamp;
             }
    },
    /**
     * multiple: only allow one file to be uploaded at a time
     */
    multiple: false,
    maxConnections: 20,
    callbacks: {
        /**
         * onSubmitted: overloaded callback that calls the callback defined
         * in the element attribute. Passes as arguments to the callback
         * a message indicating upload has started, "upload_submitted", and
         * the filename. 
         */
        onSubmitted: function(id, fileName) {
            angular.element(".qq-upload-button").hide();
            scope.eventfunc(
                {
                    message: "upload_submitted",
                    file: {filename: fileName}
                }
            );
        },
        /**
         * onComplete: overloaded callback that calls the callback defined
         * in the element attribute unless the upload failed, which will
         * fire a window alert. Passes as arguments to the callback
         * a message indicating upload has completed, "upload_complete", and
         * the filename. 
         */
        onComplete: function(id, fileName, responseJSON) {
            var errored = false;
            if(!responseJSON.success) {
                alert("Upload failed.");
                errored = true;
            } else {
                scope.eventfunc(
                    {
                        message: "upload_complete",
                        file: {
                            filename: fileName,
                            file_id: responseJSON.import_file_id,
                            source_type: scope.sourcetype,
                            source_program: scope.sourceprog,
                            source_program_version: scope.sourcever
                        }
                    }
                );
            }
        },
        /**
         * onProgress: overloaded callback that calls the callback defined
         * in the element attribute. Passes as arguments to the callback
         * a message indicating upload is in progress, "upload_in_progress", 
         * the filename, and a progress object with two keys: loaded - the 
         * bytes of the file loaded, and total - the total number of bytes 
         * for the file.
         */
        onProgress: function(id, fileName, loaded, total){
            scope.eventfunc(
                {
                    message: "upload_in_progress",
                    file: {filename: fileName},
                    progress: {
                        loaded: loaded,
                        total: total
                    }
                }
            );
        }
    },
    params: {
        'csrf_token': BE.csrftoken,
        'csrf_name': 'csrfmiddlewaretoken',
        'csrf_xname': 'X-CSRFToken',
        'import_record': scope.importrecord
        }
    });

    return uploader;
};
 
 
var makeFileSystemUploader = function(scope, element, attrs, filename) {
    var uploader = new qq.FineUploader({
        element: element[0],
        request: {
            endpoint: window.BE.urls.uploader_local_endpoint,
            paramsInBody: false,
            forceMultipart: false,
            customHeaders: {
                'X-CSRFToken': BE.csrftoken
             }
        },
        validation: {
          allowedExtensions: UPLOADER_ALLOWED_EXTENSIONS
        },
        /**
         * showMessage: callback override for error messages, e.g. 
         * "upload failed", "file too large", etc. This checks to see if the 
         * invalid extension message is the message, and uses the directive's 
         * callback in place of `window.alert` (which in turn uses a bootstrap
         * alert).
         */
        showMessage: function(message){
            var invalid_extension = "invalid extension. Valid extension(s):";
            if (message.indexOf(invalid_extension) > -1) {
                scope.eventfunc({message: "invalid_extension"});
            } else {
                window.alert(message);
            }
        },
        text: {
            uploadButton: scope.buttontext
        },
        retry: {
            enableAuto: true
        },
        iframeSupport: {
            localBlankPathPage: '/success.html'
        },
        /**
         * multiple: only allow one file to be uploaded at a time
         */
        multiple: false,
        maxConnections: 20,
        callbacks: {
            /**
             * onSubmitted: overloaded callback that calls the callback defined
             * in the element attribute. Passes as arguments to the callback
             * a message indicating upload has started, "upload_submitted", and
             * the filename. 
             */
            onSubmitted: function(id, fileName) {
                angular.element(".qq-upload-button").hide();
                scope.eventfunc(
                    {
                        message: "upload_submitted",
                        file: {filename: fileName}
                    }
                );
                var params = {
                        csrf_token: BE.csrftoken,
                        csrf_name: 'csrfmiddlewaretoken',
                        csrf_xname: 'X-CSRFToken',
                        import_record: scope.importrecord,
                        qqfilename: fileName,
                        source_type: scope.sourcetype,
                        source_program: scope.sourceprog,
                        source_program_version: scope.sourcever
                };
                
                uploader.setParams(params); //wtf fineuploader
            },
            /**
             * onComplete: overloaded callback that calls the callback defined
             * in the element attribute unless the upload failed, which will
             * fire a window alert. Passes as arguments to the callback
             * a message indicating upload has completed, "upload_complete", and
             * the filename. 
             */
            onComplete: function(id, fileName, responseJSON) {
                var errored = false;
                if(!responseJSON.success) {
                    alert("Upload failed.");
                    errored = true;
                } else {
                    scope.eventfunc(
                        {
                            message: "upload_complete",
                            file: {
                                filename: fileName,
                                file_id: responseJSON.import_file_id,
                                source_type: scope.sourcetype,
                                source_program: scope.sourceprog,
                                source_program_version: scope.sourcever
                            }
                        }
                    );
                }
            },
            /**
             * onProgress: overloaded callback that calls the callback defined
             * in the element attribute. Passes as arguments to the callback
             * a message indicating upload is in progress, "upload_in_progress", 
             * the filename, and a progress object with two keys: loaded - the 
             * bytes of the file loaded, and total - the total number of bytes 
             * for the file.
             */
            onProgress: function(id, fileName, loaded, total){
                scope.eventfunc(
                    {
                        message: "upload_in_progress",
                        file: {filename: fileName},
                        progress: {
                            loaded: loaded,
                            total: total
                        }
                    }
                );
            }
        }
    });
    return uploader;
};
 
var sdUploaderFineUploader = function(scope, element, attrs, filename) {
    var dest = window.BE.FILE_UPLOAD_DESTINATION;
    var uploader;
    if (dest === 'S3'){
        uploader = makeS3Uploader(scope, element, attrs, filename);
    } else if (dest === 'filesystem'){
        uploader = makeFileSystemUploader(scope, element, attrs, filename);
    } else {
        throw "dest " + dest + " not valid!";
    }
    $(".qq-upload-button").addClass("btn button btn-primary");
    return uploader;
};

angular.module('sdUploader', []).directive('sdUploader', function() {
    return {
        scope: {
            buttontext: "@",
            sourcetype: "@",
            eventfunc: "&",
            importrecord: "=",
            sourceprog: "@",
            sourcever: "="
        },
        restrict: 'A',
        link: function (scope, element, attrs) {
            var filename;
            $(sdUploaderFineUploader(scope, element, attrs, filename));
        }
    };
});
