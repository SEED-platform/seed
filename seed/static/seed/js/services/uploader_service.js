/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// uploader services
angular.module('BE.seed.service.uploader', []).factory('uploader_service', [
  '$http',
  '$q',
  '$timeout',
  'user_service',
  function ($http, $q, $timeout, user_service) {

    var uploader_factory = {};

    uploader_factory.get_AWS_creds = function () {
      return $http.get(window.BE.urls.get_AWS_creds).then(function (response) {
        return response.data;
      });
    };
    /**
     * create_dataset: AJAX request to create a new dataset/import record
     * should have a response like:
     *  {
     *       "status": "success",
     *       "import_record_id": 4,
     *       "import_record_name": "2013 city compliance dataset"
     *  }
     * or
     *  {
     *        "status": "error",
     *        "message": "name already in use"
     *  }
     */
    uploader_factory.create_dataset = function (dataset_name) {
      // timeout here for testing
      return $http.post('/api/v2/datasets/', {
        name: dataset_name
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * save_raw_data
     * This service call will simply call a view on the backend to save raw
     * data into BuildingSnapshot instances.
     * @param file_id: the pk of a ImportFile object we're going to save raw.
     */
    uploader_factory.save_raw_data = function (file_id, cycle_id) {
      return $http.post('/api/v2/import_files/' + file_id + '/save_raw_data/', {
        cycle_id: cycle_id,
        organization_id: user_service.get_organization().id
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * check_progress: gets the progress for saves, maps, and matches
     * @param progress_key: progress_key to grab the progress
     */
    uploader_factory.check_progress = function (progress_key) {
      return $http.post('/api/v2/progress/', {
        progress_key: progress_key
      }).then(function (response) {
        if (response.data.status === 'error') return $q.reject(response);
        else return response.data;
      });
    };
    /**
     * check_progress_loop: check loop to update the progress bar
     *
     * @param {string} progress_key: key
     * @param {number} offset: where to start the progress bar
     * @param {number} multiplier: multiplier for progress val
     * @param {fn} success_fn: function to call when progress is done
     * @param {fn} failure_fn: function to call when progress is done and the result was not success
     * @param {obj} progress_bar_obj: progress bar object, attr 'progress'
     *   is set with the progress
     */
    uploader_factory.check_progress_loop = function (progress_key, offset, multiplier, success_fn, failure_fn, progress_bar_obj, debug) {
      debug = !_.isUndefined(debug);
      uploader_factory.check_progress(progress_key).then(function (data) {
        $timeout(function () {
          progress_bar_obj.progress = (data.progress * multiplier) + offset;
          if (data.progress < 100) {
            uploader_factory.check_progress_loop(progress_key, offset, multiplier, success_fn, failure_fn, progress_bar_obj, debug);
          } else {
            success_fn(data);
          }
        }, 750);
      }, failure_fn);
    };

    return uploader_factory;
  }]);
