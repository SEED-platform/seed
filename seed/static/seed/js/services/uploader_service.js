/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
      return $http.post('/api/v3/datasets/', {
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
     * validate_use_cases
     * This service call will simply call a view on the backend to validate
     * BuildingSync files with use cases
     * @param file_id: the pk of a ImportFile object we're going to save raw.
     */
    uploader_factory.validate_use_cases = function (file_id) {
      var org_id = user_service.get_organization().id;
      return $http.post('/api/v3/import_files/' + file_id + '/validate_use_cases/?organization_id=' + org_id.toString())
        .then(function (response) {
          return response.data;
        })
        .catch(function (err) {
          if (err.data.status === 'error') {
            return err.data;
          }
          // something unexpected happened... throw it
          throw err;
        });
    };

    /**
     * save_raw_data
     * This service call will simply call a view on the backend to save raw
     * data into BuildingSnapshot instances.
     * @param file_id: the pk of a ImportFile object we're going to save raw.
     */
    uploader_factory.save_raw_data = function (file_id, cycle_id) {
      return $http.post('/api/v3/import_files/' + file_id + '/start_save_data/', {
        cycle_id: cycle_id,
      }, {
        params: { organization_id: user_service.get_organization().id }
      }).then(function (response) {
        return response.data;
      });
    };

    /**
     * check_progress: gets the progress for saves, maps, and matches
     * @param progress_key: progress_key to grab the progress
     */
    uploader_factory.check_progress = function (progress_key) {
      return $http.get('/api/v3/progress/' + progress_key + '/').then(function (response) {
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
          right_now = Date.now();
          progress_bar_obj.progress_last_checked = right_now;

          new_progress_value = _.clamp((data.progress * multiplier) + offset, 0, 100);
          updating_progress = new_progress_value != progress_bar_obj.progress || progress_bar_obj.status_message != data.status_message;
          if (updating_progress) {
            progress_bar_obj.progress_last_updated = right_now;
          }

          progress_bar_obj.progress = new_progress_value;
          progress_bar_obj.status_message = data.status_message;
          if (data.progress < 100) {
            uploader_factory.check_progress_loop(progress_key, offset, multiplier, success_fn, failure_fn, progress_bar_obj, debug);
          } else {
            success_fn(data);
          }
        }, 750);
      }, failure_fn);
    };

    uploader_factory.pm_meters_preview = function (file_id, org_id) {
      return $http.get(
        '/api/v3/import_files/' + file_id + '/pm_meters_preview/',
        { params: { organization_id: org_id } }
      ).then(function (response) {
        return response.data;
      });
    };

    uploader_factory.greenbutton_meters_preview = function (file_id, org_id, view_id) {
      return $http.get(
        '/api/v3/import_files/' + file_id + '/greenbutton_meters_preview/',
        { params: { organization_id: org_id, view_id } }
      ).then(function (response) {
        return response.data;
      });
    };

    return uploader_factory;
  }]);
