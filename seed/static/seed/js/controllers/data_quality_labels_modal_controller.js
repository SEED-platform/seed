/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 *
 * Controller for the Update Labels modal window.
 * Manages applying labels to a single Property or Tax Lot, as
 * well as allowing for the creation of new labels.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 *
 *
 */
angular.module('BE.seed.controller.data_quality_labels_modal', [])
  .controller('data_quality_labels_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'label_service',
    'Notification',
    'org_id',
    function ($scope, $uibModalInstance, label_service, notification, org_id) {
      //keep track of status of service call
      $scope.loading = false;

      //An array of all available labels in the system.
      //These label objects should have the is_applied property set so
      //the modal can show the Remove button if necessary. (Populated
      //during init function below.)
      $scope.labels = [];

      //new_label serves as model for the "Create a new label" UI
      $scope.new_label = {};

      //list of colors for the create label UI
      $scope.available_colors = label_service.get_available_colors();

      /* Initialize the label props for a 'new' label */
      $scope.initialize_new_label = function () {
        $scope.new_label = {
          color: 'gray',
          label: 'default',
          name: ''
        };
      };

      /* Create a new label based on user input */
      $scope.submitNewLabelForm = function (form) {
        $scope.createdLabel = null;
        if (form.$invalid) return;
        label_service.create_label($scope.new_label).then(function (data) {
          var createdLabel = data;

          $scope.newLabelForm.$setPristine();
          $scope.labels.unshift(createdLabel);
          $scope.initialize_new_label();
        }, function (data) {
          // label name already exists
          if (data.message === 'label already exists') {
            alert('label already exists');
          } else {
            alert('error creating new label');
          }
        });
      };

      /* Toggle the add button for a label */
      $scope.toggle_add = function (label) {
        // console.log(label)
        $uibModalInstance.close(label);
      };

      /* User has cancelled dialog */
      $scope.cancel = function () {
        //don't do anything, just close modal.
        $uibModalInstance.dismiss('cancel');
      };

      /* init: Gets the list of labels. Sets up new label object. */
      var init = function () {
        $scope.initialize_new_label();
        //get labels with 'is_applied' property by passing in current search state
        $scope.loading = true;
        label_service.get_labels_for_org(org_id).then(function (labels) {
          $scope.labels = labels;
          $scope.loading = false;
        });
      };

      init();

    }]);
