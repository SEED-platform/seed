/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.building_detail_update_labels_modal_ctrl', [])
.controller('building_detail_update_labels_modal_ctrl', [
  '$scope',
  '$uibModalInstance',
  'label_service',
  'building',
  'Notification',
  function ($scope, $uibModalInstance, label_service, building, notification) {

    //Controller for the Update Building Labels modal window.
    //Manages applying labels to a single buildings, as
    //well as allowing for the creation of new labels.

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
    $scope.initialize_new_label = function() {
       $scope.new_label = {color:"gray", label:"default", name:""};
    };

    /* Create a new label based on user input */
    $scope.submitNewLabelForm = function(form){
        $scope.createdLabel = null;
        if (form.$invalid) {
            return;
        }
        label_service.create_label($scope.new_label).then(
            function(data){

                //promise completed successfully
                var createdLabel = data;

                //Assume that user wants to apply a label they just created
                //in this modal...
                createdLabel.is_checked_add = true;

                $scope.newLabelForm.$setPristine();
                $scope.labels.unshift(createdLabel);
                $scope.initialize_new_label();
            },
            function(data, status) {
                // reject promise
                // label name already exists
                if (data.message==='label already exists'){
                    alert('label already exists');
                } else {
                    alert('error creating new label');
                }
            }
        );
    };

    /* Toggle the add button for a label */
    $scope.toggle_add = function(label){
        if (label.is_checked_remove && label.is_checked_add) {
            label.is_checked_remove = false;
        }
    };

    /* Toggle the remove button for a label */
    $scope.toggle_remove = function(label){
        if (label.is_checked_remove && label.is_checked_add) {
            label.is_checked_add = false;
        }
    };

    /* User has indicated 'Done' so perform selected label operations */
    $scope.done = function () {

        var addLabelIDs = _.chain($scope.labels)
            .filter(function(lbl) {
                return lbl.is_checked_add;
            })
            .pluck("id")
            .value();
        var removeLabelIDs = _.chain($scope.labels)
            .filter(function(lbl) {
                return lbl.is_checked_remove;
            })
            .pluck("id")
            .value();

        label_service.update_building_labels(addLabelIDs, removeLabelIDs, [building.pk], false, {}).then(
            function(data){
                var msg = data.num_buildings_updated.toString() + " buildings updated.";
                notification.primary(msg);
                $uibModalInstance.close();
            },
            function(data, status) {
            }
        );
    };

    /* User has cancelled dialog */
    $scope.cancel = function () {
        //don't do anything, just close modal.
        $uibModalInstance.dismiss('cancel');
    };

    /* init: Gets the list of labels. Sets up new label object. */
    var init = function() {
        $scope.initialize_new_label();
        //get labels with 'is_applied' property by passing in current search state
        $scope.loading = true;
        label_service.get_labels([building.pk], false, {}).then(function(data){
             $scope.labels = data.results;
             $scope.loading = false;
        });
    };

    init();

}]);
