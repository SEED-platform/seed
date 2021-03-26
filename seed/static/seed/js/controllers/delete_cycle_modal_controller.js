/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_cycle_modal', [])
  .controller('delete_cycle_modal_controller', [
    '$scope',
    '$window',
    '$state',
    '$q',
    '$uibModalInstance',
    'inventory_service',
    'user_service',
    'cycle_service',
    'uploader_service',
    'cycle',
    'organization_id',
    function ($scope, $window, $state, $q, $uibModalInstance, inventory_service, user_service, cycle_service, uploader_service, cycle, organization_id) {
      $scope.cycle_id = cycle.cycle_id;
      $scope.cycle_name = cycle.name;
      $scope.organization_id = organization_id;

      $scope.cycle_has_properties = cycle.num_properties > 0;
      $scope.cycle_has_taxlots = cycle.num_taxlots > 0;
      $scope.cycle_has_inventory = $scope.cycle_has_properties || $scope.cycle_has_taxlots;
      $scope.delete_cycle_status = null;
      $scope.error_occurred = false;

      /**
       * uploader: hold the state of the upload.
       * in_progress: bool - when true: shows the progress bar and hides the
       *  upload button. when false: hides the progress bar and shows the upload
       *  button.
       * progress: int or float - the progress bar value, i.e. percentage complete
       * complete: bool - true when the upload has finished
       * status_message: str - status of the task
       * progress_last_updated: null | int - when not null it indicates the last time the progress bar changed (UNIX Epoch in ms)
       * progress_last_checked: null | int - when not null it indicates the last time the progress was checked (UNIX Epoch in ms)
       */
      $scope.uploader = {
        in_progress: false,
        progress: 0,
        complete: false,
        status_message: '',
        progress_last_updated: null,
        progress_last_checked: null
      };

      // open an inventory list page in a new tab
      $scope.goToInventoryList = function (inventory_type) {
        user_service.set_organization(
          { id: organization_id }
        ).then(function (response) {
          inventory_service.save_last_cycle($scope.cycle_id);
          const inventory_url = $state.href('inventory_list', {inventory_type: inventory_type});
          $window.open(inventory_url, '_blank');
          // refresh the current page b/c we have modified the default organization
          location.reload();
        }).catch(function (response) {
          console.error('Failed to set default org: ');
          console.error(response);
          $scope.error_occurred = true;
        })
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };

      // user confirmed deletion of cycle
      $scope.confirmDelete = function () {
        $scope.delete_cycle_status = 'pending';
        $scope.uploader.in_progress = true;
        cycle_service.delete_cycle($scope.cycle_id, $scope.organization_id)
          .then(function (data) {
            function successHandler() {
              $scope.delete_cycle_status = 'success';
              $scope.uploader.in_progress = false;
            }
            function errorHandler(err) {
              console.error('Failed to delete cycle: ');
              console.error(err);
              $scope.delete_cycle_status = 'failed';
              $scope.error_occurred = true;
              $scope.uploader.in_progress = false;
            }
            uploader_service.check_progress_loop(
              data.progress_key,
              0,
              1,
              successHandler,
              errorHandler,
              $scope.uploader,
            );
          })
          .catch(function (res) {
            console.error('Failed to delete cycle: ');
            console.error(res);
            $scope.delete_cycle_status = 'failed';
            $scope.error_occurred = true;
            $scope.uploader.in_progress = false;
          });
      };
    }]);
