/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
 * directive sd-uploader: wraps fineuploader.js assumed AWS creds are in global
 *                        namespace: window.config.AWS_UPLOAD_BUCKET_NAME window.config.AWS_CLIENT_ACCESS_KEY
 *   sourcetype: string - upon upload successful, send the sourcetype param to
 *                        the server to store the linked file
 *   eventfunc: callback function with three arguments: `message`, `filename`, `progress`
 *              `message` - string - options: "upload_submitted",
 *              "upload_in_progress", "upload_complete", "upload_error", and "invalid_extension"
 *              `filename` - string name of the file uploaded
 *              `progress` - JS object with keys `loaded` and `total` where
 *                           `loaded` / `total` * 100.0 is the percent uploaded
 *  importrecord - int or string - id of import record or dataset
 *
 */
var UPLOADER_ALLOWED_EXTENSIONS = ['csv', 'xls', 'xlsx'];

var makeS3Uploader = function (scope, element) {
  var uploader = new qq.s3.FineUploaderBasic({
    button: element[0],
    request: {
      endpoint: document.location.protocol + '//' + window.BE.AWS_UPLOAD_BUCKET_NAME + '.s3.amazonaws.com',
      accessKey: window.BE.AWS_CLIENT_ACCESS_KEY,
      params: {category: 'data_imports'}
    },
    validation: {
      allowedExtensions: UPLOADER_ALLOWED_EXTENSIONS
    },
    retry: {
      enableAuto: true
    },
    signature: {
      endpoint: '/api/v2/sign_policy_document/',
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
      endpoint: '/api/v2/s3_upload_complete/',
      params: {
        csrfmiddlewaretoken: BE.csrftoken,
        import_record: scope.importrecord,
        source_type: scope.sourcetype,
        source_program: scope.sourceprog,
        source_program_version: scope.sourcever
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
      key: function (fileId) {
        var filename = encodeURIComponent(uploader.getName(fileId));
        var timestamp = Math.round(new Date().getTime() / 1000);
        return 'data_imports/' + filename + '.' + timestamp;
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
      onSubmitted: function (id, fileName) {
        scope.eventfunc(
          {
            message: 'upload_submitted',
            file: {
              filename: fileName,
              source_type: scope.sourcetype
            }
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
      onComplete: function (id, fileName, responseJSON) {
        if (!responseJSON.success) {
          alert('Upload failed.');
        } else {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              file_id: responseJSON.import_file_id,
              source_type: scope.sourcetype,
              source_program: scope.sourceprog,
              source_program_version: scope.sourcever
            }
          });
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
      onProgress: function (id, fileName, loaded, total) {
        scope.eventfunc(
          {
            message: 'upload_in_progress',
            file: {
              filename: fileName,
              source_type: scope.sourcetype
            },
            progress: {
              loaded: loaded,
              total: total
            }
          }
        );
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError: function (id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({message: 'invalid_extension'});
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g. invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        var error = errorReason;
        try {
          var json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {}

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error: error
          }
        });
      }
    },
    params: {
      csrf_token: BE.csrftoken,
      csrf_name: 'csrfmiddlewaretoken',
      csrf_xname: 'X-CSRFToken',
      import_record: scope.importrecord
    }
  });

  return uploader;
};


var makeFileSystemUploader = function (scope, element) {
  var uploader = new qq.FineUploaderBasic({
    button: element[0],
    request: {
      endpoint: '/api/v2/upload/',
      paramsInBody: true,
      forceMultipart: true,
      customHeaders: {
        'X-CSRFToken': BE.csrftoken
      }
    },
    validation: {
      allowedExtensions: UPLOADER_ALLOWED_EXTENSIONS
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
      onSubmitted: function (id, fileName) {
        scope.eventfunc(
          {
            message: 'upload_submitted',
            file: {
              filename: fileName,
              source_type: scope.sourcetype
            }
          }
        );
        var params = {
          csrf_token: BE.csrftoken,
          csrf_name: 'csrfmiddlewaretoken',
          csrf_xname: 'X-CSRFToken',
          import_record: scope.importrecord,
          file: fileName,
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
      onComplete: function (id, fileName, responseJSON) {
        if (!responseJSON.success) {
          alert('Upload failed.');
        } else {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              file_id: responseJSON.import_file_id,
              cycle_id: (scope.sourceprog === 'PortfolioManager' && scope.$parent.useField) ? 'year_ending' : scope.$parent.selectedCycle.id,
              source_type: scope.sourcetype,
              source_program: scope.sourceprog,
              source_program_version: scope.sourcever
            }
          });
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
      onProgress: function (id, fileName, loaded, total) {
        scope.eventfunc({
          message: 'upload_in_progress',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          },
          progress: {
            loaded: loaded,
            total: total
          }
        });
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError: function (id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({message: 'invalid_extension'});
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g. invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        var error = errorReason;
        try {
          var json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {}

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error: error
          }
        });
      }
    }
  });
  return uploader;
};

var makeBuildingSyncUploader = function (scope, element) {
  var uploader = new qq.FineUploaderBasic({
    button: element[0],
    request: {
      endpoint: '/api/v2/building_file/',
      inputName: 'file',
      paramsInBody: true,
      forceMultipart: true,
      customHeaders: {
        'X-CSRFToken': BE.csrftoken
      }
    },
    validation: {
      allowedExtensions: ['xml']
    },
    text: {
      uploadButton: scope.buttontext
    },
    retry: {
      enableAuto: false
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
      onSubmitted: function (id, fileName) {
        scope.eventfunc({
          message: 'upload_submitted',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          }
        });
        var params = {
          csrf_token: BE.csrftoken,
          csrf_name: 'csrfmiddlewaretoken',
          csrf_xname: 'X-CSRFToken',
          file_type: 1,
          organization_id: scope.organizationId,
          cycle_id: scope.cycleId
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
      onComplete: function (id, fileName, responseJSON) {
        // Only handle success because error transition is in onError event handler
        if (responseJSON.status === 'success') {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              view_id: _.get(responseJSON, 'data.property_view.id'),
              cycle_id: (scope.sourceprog === 'PortfolioManager' && scope.$parent.useField) ? 'year_ending' : scope.$parent.selectedCycle.id,
              source_type: scope.sourcetype
            }
          });
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
      onProgress: function (id, fileName, loaded, total) {
        scope.eventfunc({
          message: 'upload_in_progress',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          },
          progress: {
            loaded: loaded,
            total: total
          }
        });
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError: function (id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({message: 'invalid_extension'});
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g. invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        var error = errorReason;
        try {
          var json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {}

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error: error
          }
        });
      }
    }
  });
  return uploader;
};

var makeBuildingSyncUpdater = function (scope, element) {
  var uploader = new qq.FineUploaderBasic({
    button: element[0],
    method: 'PUT',
    request: {
      endpoint: '/api/v2.1/properties/' + scope.importrecord + '/update_with_building_sync/',
      inputName: 'file',
      paramsInBody: true,
      forceMultipart: true,
      customHeaders: {
        'X-CSRFToken': BE.csrftoken
      }
    },
    validation: {
      allowedExtensions: ['xml']
    },
    text: {
      uploadButton: scope.buttontext
    },
    retry: {
      enableAuto: false
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
      onSubmitted: function (id, fileName) {
        scope.eventfunc({
          message: 'upload_submitted',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          }
        });
        var params = {
          csrf_token: BE.csrftoken,
          csrf_name: 'csrfmiddlewaretoken',
          csrf_xname: 'X-CSRFToken',
          file_type: 1,
          organization_id: scope.organizationId,
          cycle_id: scope.cycleId
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
      onComplete: function (id, fileName, responseJSON) {
        // Only handle success because error transition is in onError event handler
        if (responseJSON.status === 'success') {
          scope.eventfunc({
            message: 'upload_complete',
            file: {
              filename: fileName,
              view_id: _.get(responseJSON, 'data.property_view.id'),
              cycle_id: (scope.sourceprog === 'PortfolioManager' && scope.$parent.useField) ? 'year_ending' : scope.$parent.selectedCycle.id,
              source_type: scope.sourcetype
            }
          });
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
      onProgress: function (id, fileName, loaded, total) {
        scope.eventfunc({
          message: 'upload_in_progress',
          file: {
            filename: fileName,
            source_type: scope.sourcetype
          },
          progress: {
            loaded: loaded,
            total: total
          }
        });
      },
      /**
       * onError: overloaded callback that calls the callback defined
       * in the element attribute. Primarily for non-conforming files
       * that return 400 from the backend and invalid file extensions.
       */
      onError: function (id, fileName, errorReason, xhr) {
        if (_.includes(errorReason, ' has an invalid extension.')) {
          scope.eventfunc({message: 'invalid_extension'});
          return;
        }

        // Ignore this error handler if the network request hasn't taken place yet (e.g. invalid file extension)
        if (!xhr) {
          alert(errorReason);
          return;
        }

        var error = errorReason;
        try {
          var json = JSON.parse(xhr.responseText);
          if (_.has(json, 'message')) {
            error = json.message;
          }
        } catch (e) {}

        scope.eventfunc({
          message: 'upload_error',
          file: {
            filename: fileName,
            source_type: scope.sourcetype,
            error: error
          }
        });
      }
    }
  });
  return uploader;
};

var sdUploaderFineUploader = function (scope, element, attrs, filename) {
  var dest = window.BE.FILE_UPLOAD_DESTINATION;
  var uploader;
  if (scope.sourcetype === 'BuildingSync') {
    uploader = makeBuildingSyncUploader(scope, element, attrs, filename);
  } else if (scope.sourcetype === 'BuildingSyncUpdate') {
    uploader = makeBuildingSyncUpdater(scope, element, attrs, filename);
  } else if (dest === 'S3') {
    uploader = makeS3Uploader(scope, element, attrs, filename);
  } else if (dest === 'filesystem') {
    uploader = makeFileSystemUploader(scope, element, attrs, filename);
  } else {
    throw 'dest ' + dest + ' not valid!';
  }
  return uploader;
};

angular.module('sdUploader', []).directive('sdUploader', function () {
  return {
    scope: {
      cycleId: '=',
      eventfunc: '&',
      importrecord: '=',
      organizationId: '=',
      sourceprog: '@',
      sourcetype: '@',
      sourcever: '='
    },
    restrict: 'A',
    link: function (scope, element, attrs) {
      $(sdUploaderFineUploader(scope, element, attrs));
    }
  };
});
