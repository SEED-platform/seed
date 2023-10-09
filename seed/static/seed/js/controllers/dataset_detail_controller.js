/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.dataset_detail', []).controller('dataset_detail_controller', [
  '$scope',
  'dataset_payload',
  '$log',
  'dataset_service',
  'cycles',
  '$uibModal',
  'urls',
  function ($scope, dataset_payload, $log, dataset_service, cycles, $uibModal, urls) {
    $scope.dataset = dataset_payload.dataset;

    _.forOwn($scope.dataset.importfiles, (value) => {
      value.created = new Date(value.created);
    });

    $scope.confirm_delete = function (file) {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/delete_file_modal.html`,
        controller: 'delete_file_modal_controller',
        resolve: {
          file
        }
      });

      modalInstance.result.finally(() => {
        init();
      });
    };

    /**
     * open_data_upload_modal: opens the data upload modal to step 4, add energy files
     */
    $scope.open_data_upload_modal = function () {
      const dataModalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/data_upload_modal.html`,
        controller: 'data_upload_modal_controller',
        resolve: {
          cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
          step: _.constant(2),
          dataset: () => $scope.dataset,
          organization: () => $scope.menu.user.organization
        }
      });

      dataModalInstance.result.finally(() => {
        init();
      });
    };

    $scope.getCycleName = function (id) {
      const cycle = _.find(cycles.cycles, { id });
      return cycle ? cycle.name : undefined;
    };

    $scope.downloadUrl = (importFile) => {
      const segments = importFile.file.split(/[\\/]/);
      return `/api/v3/media/${segments.slice(segments.indexOf('media') + 1).join('/')}`;
    };

    var init = function () {
      dataset_service.get_dataset($scope.dataset.id).then((data) => {
        $scope.dataset = data.dataset;
      });
    };
  }
]);
