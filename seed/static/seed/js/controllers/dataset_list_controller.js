/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.dataset', []).controller('dataset_list_controller', [
  '$scope',
  '$rootScope',
  'datasets_payload',
  '$uibModal',
  'urls',
  'dataset_service',
  // eslint-disable-next-line func-names
  function ($scope, $rootScope, datasets_payload, $uibModal, urls, dataset_service) {
    $scope.datasets = datasets_payload.datasets;
    $scope.columns = [
      {
        title: 'Data Set Name'
      },
      {
        title: '# Of Files'
      },
      {
        title: 'Last Changed'
      },
      {
        title: 'Changed By'
      },
      {
        title: 'Actions'
      }
    ];

    /**
     * refresh_datasets: refreshes dataset list
     */
    const refresh_datasets = () => {
      dataset_service.get_datasets().then((data) => {
        $scope.datasets = data.datasets;
      });
    };

    /**
     * Functions for dealing with editing a dataset's name
     */
    $scope.edit_dataset_name = (dataset) => {
      dataset.edit_form_showing = true;
      dataset.old_name = dataset.name;
    };
    $scope.cancel_edit_name = (dataset) => {
      dataset.name = dataset.old_name;
      dataset.edit_form_showing = false;
    };
    $scope.save_dataset_name = (dataset) => {
      if (dataset.name !== dataset.old_name) {
        dataset_service.update_dataset(dataset).then(() => {
          refresh_datasets();
        });
        dataset.edit_form_showing = false;
      }
    };

    /**
     * open_data_upload_modal: opens the data upload modal to step 4, add energy files
     */
    $scope.open_data_upload_modal = (dataset) => {
      let step = 2;
      if (_.isUndefined(dataset)) {
        step = 1;
        dataset = {};
      } else if ($scope.missing_assessor_files(dataset)) {
        step = 2;
      }
      const dataModalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/data_upload_modal.html`,
        controller: 'data_upload_modal_controller',
        resolve: {
          cycles: ['cycle_service', (cycle_service) => cycle_service.get_cycles()],
          step: () => step,
          dataset: () => dataset,
          organization: () => $scope.menu.user.organization
        }
      });

      dataModalInstance.result.finally(() => {
        refresh_datasets();
      });
    };

    $scope.confirm_delete = (dataset) => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/delete_dataset_modal.html`,
        controller: 'delete_dataset_modal_controller',
        resolve: {
          dataset
        }
      });

      modalInstance.result.finally(() => {
        refresh_datasets();
      });
    };

    /**
     * missing_assessor_files: true if the dataset has no assessed files
     */
    $scope.missing_assessor_files = (dataset) => {
      for (let i = 0; i < dataset.importfiles.length; i++) {
        const importfile = dataset.importfiles[i];
        if (importfile.source_type === 'Assessed Raw') {
          return false;
        }
      }
      return true;
    };

    /**
     * missing_pm_files: true if the dataset has no Portfolio Manager files
     */
    $scope.missing_pm_files = (dataset) => {
      for (let i = 0; i < dataset.importfiles.length; i++) {
        const importfile = dataset.importfiles[i];
        if (importfile.source_type === 'Portfolio Raw') {
          return false;
        }
      }
      return true;
    };

    /**
     * event broadcast from menu controller when a new dataset is added
     */
    $scope.$on('datasets_updated', refresh_datasets);
    $rootScope.$on('datasets_updated', refresh_datasets);
  }
]);
