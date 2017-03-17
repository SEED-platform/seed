/**
 * :copyright: (c) 2014 Building Energy Inc
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

      _.forOwn($scope.dataset.importfiles, function (value, key) {
        value['created'] = new Date(value['created']);
      });

      $scope.confirm_delete = function (file) {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/delete_file_modal.html',
          controller: 'delete_file_modal_controller',
          resolve: {
            file: file
          }
        });

        modalInstance.result.then(
          // modal close() function
          function () {
            init();
            // modal dismiss() function
          }, function (message) {
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
            step: function () {
              return 2;
            },
            dataset: function () {
              return $scope.dataset;
            }
          }
        });

        dataModalInstance.result.then(
          // modal close() function
          function () {
            init();
            // modal dismiss() function
          }, function (message) {
            // dismiss
            init();
          });
      };

      $scope.getCycleName = function (id) {
        var cycle = _.find(cycles.cycles, {id: id});
        return cycle ? cycle.name : undefined;
      };

      var init = function () {
        dataset_service.get_dataset($scope.dataset.id).then(function (data) {
          // resolve promise
          $scope.dataset = data.dataset;
        });
      };

    }]);
