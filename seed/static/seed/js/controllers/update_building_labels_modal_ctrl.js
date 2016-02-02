/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.update_building_labels_modal', [])
.controller('update_building_labels_modal_ctrl', [
  '$scope',
  '$uibModalInstance',
  'label_service',
  'search',
  'Notification',
  function ($scope, $uibModalInstance, label_service, search, notification) {

    //Controller for the Update Building Labels modal window.
    //Manages applying labels to a pre-selected set of buildings, as
    //well as allowing for the creation of new labels.

    //keep track of status of service call
    $scope.loading = false;

    //convenience refs for the parts of the search object we're concerned about in this controller
    var selected_buildings = search.selected_buildings;
    var select_all_checkbox = search.select_all_checkbox;
    var filter_params = search.filter_params;

    //If the user has checkmarked individual buildings, bind how many buildings are selected.
    //Otherwise, UI will show default message ("..from selected buildings")
    if (search.selected_buildings && search.selected_buildings.length > 0){
        $scope.number_matching_search = search.selected_buildings.length;
    } else {
        $scope.number_matching_search = "";
    }
    
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

        // Parameters used to limit the loaded building list.
        var search_params = search.construct_search_query();

        label_service.update_building_labels(addLabelIDs, removeLabelIDs, selected_buildings, select_all_checkbox, search_params).then(
            function(data){  
                var msg = data.num_buildings_updated.toString() + " buildings updated.";
                notification.primary(msg);       
                $uibModalInstance.close();
            },
            function(data, status) {
               // Rejected promise, error occurred.
               // TODO: Make this nicer...just doing alert for development
               alert('Error updating building labels: ' + status);
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
        var search_params = search.construct_search_query();
        label_service.get_labels(selected_buildings, select_all_checkbox, search_params).then(function(data){
             $scope.labels = data.results;
             $scope.loading = false;
        });
    }; 

    init();

}]);
