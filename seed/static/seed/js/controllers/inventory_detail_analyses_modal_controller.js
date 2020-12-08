/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 *
 * Controller for the analysis modal.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 *
 *
 */
angular.module('BE.seed.controller.inventory_detail_analyses_modal', [])
  .controller('inventory_detail_analyses_modal_controller', [
    '$scope',
    '$log',
    '$uibModalInstance',
    'inventory_ids',
    'inventory_type',
    'Notification',
    function ($scope, $log, $uibModalInstance, inventory_ids, inventory_type, meters, notification) {
      $scope.meters = meters;
      $scope.inventory_ids = inventory_ids;
      $scope.inventory_type = inventory_type;
      //keep track of status of service call
      $scope.loading = false;
      /* Create a new analysis based on user input */
      $scope.submitNewAnalysisForm = function (form) {
        //create new analysis here
      };

      /* User has cancelled dialog */
      $scope.cancel = function () {
        //don't do anything, just close modal.
        $uibModalInstance.dismiss('cancel');
      };

      /* init: Gets the list of labels. Sets up new label object. */
      var init = function () {
        $scope.loading = true;
      };

      init();

    }]);
