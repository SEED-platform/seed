/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.dataset', [])
  .controller('dataset_list_controller', [
    '$scope',
    'datasets_payload',
    '$uibModal',
    'urls',
    'dataset_service',
    function ($scope, datasets_payload, $uibModal, urls, dataset_service) {
      $scope.datasets = datasets_payload.datasets;
      $scope.columns = [{
        title: 'Data Set Name'
      }, {
        title: '# Of Files'
      }, {
        title: 'Last Changed'
      }, {
        title: 'Changed By'
      }, {
        title: 'Actions'
      }];
      /**
       * Functions for dealing with editing a dataset's name
       */
      $scope.edit_dataset_name = function (dataset) {
        dataset.edit_form_showing = true;
        dataset.old_name = dataset.name;
      };
      $scope.cancel_edit_name = function (dataset) {
        dataset.name = dataset.old_name;
        dataset.edit_form_showing = false;
      };
      $scope.save_dataset_name = function (dataset) {
        if (dataset.name !== dataset.old_name) {
          dataset_service.update_dataset(dataset).then(function () {
            refresh_datasets();
          });
          dataset.edit_form_showing = false;
        }
      };

      /**
       * open_data_upload_modal: opens the data upload modal to step 4, add energy files
       */
      $scope.open_data_upload_modal = function (dataset) {
        var step = 2;
        if (_.isUndefined(dataset)) {
          step = 1;
          dataset = {};
        } else if ($scope.missing_assessor_files(dataset)) {
          step = 2;
        }
        var dataModalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/data_upload_modal.html',
          controller: 'data_upload_modal_controller',
          resolve: {
            cycles: ['cycle_service', function (cycle_service) {
              return cycle_service.get_cycles();
            }],
            step: function () {
              return step;
            },
            dataset: function () {
              return dataset;
            },
            organization: function () {
              return $scope.menu.user.organization;
            }
          }
        });

        dataModalInstance.result.finally(function () {
          refresh_datasets();
        });
      };

      $scope.confirm_delete = function (dataset) {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/delete_dataset_modal.html',
          controller: 'delete_dataset_modal_controller',
          resolve: {
            dataset: dataset
          }
        });

        modalInstance.result.finally(function () {
          refresh_datasets();
        });
      };

      /**
       * missing_assessor_files: true if the dataset has no assessed files
       */
      $scope.missing_assessor_files = function (dataset) {
        for (var i = 0; i < dataset.importfiles.length; i++) {
          var importfile = dataset.importfiles[i];
          if (importfile.source_type === 'Assessed Raw') {
            return false;
          }
        }
        return true;
      };

      /**
       * missing_pm_files: true if the dataset has no Portfolio Manager files
       */
      $scope.missing_pm_files = function (dataset) {
        for (var i = 0; i < dataset.importfiles.length; i++) {
          var importfile = dataset.importfiles[i];
          if (importfile.source_type === 'Portfolio Raw') {
            return false;
          }
        }
        return true;
      };

      /**
       * refresh_datasets: refreshes dataset list
       */
      var refresh_datasets = function () {
        dataset_service.get_datasets().then(function (data) {
          $scope.datasets = data.datasets;
        });
      };

      /**
       * event broadcast from menu controller when a new dataset is added
       */
      $scope.$on('datasets_updated', refresh_datasets);

    }
  ]);
