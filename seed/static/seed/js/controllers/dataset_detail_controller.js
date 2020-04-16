/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.dataset_detail', [])
  .controller('dataset_detail_controller', [
    '$scope',
    'dataset_payload',
    '$log',
    'dataset_service',
    'cycles',
    '$uibModal',
    'urls',
    function ($scope, dataset_payload, $log, dataset_service, cycles, $uibModal, urls) {
      $scope.dataset = dataset_payload.dataset;

      _.forOwn($scope.dataset.importfiles, function (value) {
        value.created = new Date(value.created);
      });

      $scope.confirm_delete = function (file) {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/delete_file_modal.html',
          controller: 'delete_file_modal_controller',
          resolve: {
            file: file
          }
        });

        modalInstance.result.finally(function () {
          init();
        });
      };

      /**
       * open_data_upload_modal: opens the data upload modal to step 4, add energy files
       */
      $scope.open_data_upload_modal = function () {
        var dataModalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/data_upload_modal.html',
          controller: 'data_upload_modal_controller',
          resolve: {
            cycles: ['cycle_service', function (cycle_service) {
              return cycle_service.get_cycles();
            }],
            step: _.constant(2),
            dataset: function () {
              return $scope.dataset;
            },
            organization: function () {
              return $scope.menu.user.organization;
            }
          }
        });

        dataModalInstance.result.finally(function () {
          init();
        });
      };

      $scope.getCycleName = function (id) {
        var cycle = _.find(cycles.cycles, {id: id});
        return cycle ? cycle.name : undefined;
      };

      var init = function () {
        dataset_service.get_dataset($scope.dataset.id).then(function (data) {
          $scope.dataset = data.dataset;
        });
      };

    }]);
