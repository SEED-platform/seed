

angular.module('BE.seed.controller.update_building_labels_modal', [])
.controller('update_building_labels_modal_ctrl', [
  '$scope',
  '$uibModalInstance',
  'label_service',
  'labels',
  'search',
  'Notification',
  function ($scope, $uibModalInstance, label_service, labels, search, notification) {

    //If the user has checkmarked buildings, bind how many buildings are selected.
    //Otherwise, UI will show default message ("..from selected buildings")
    if (search.selected_buildings && search.selected_buildings.length > 0){
        $scope.number_matching_search = search.selected_buildings.length;
    } else {
        $scope.number_matching_search = "";
    }
    
    //An array of labels relevant to the current search properties.
    //These label objects should have the is_applied property set so 
    //the modal can show the Remove button if necessary.
    $scope.labels = labels;

    //new_label serves as model for the "Create a new label" UI
    $scope.new_label = {};

    //list of colors for the create label UI
    $scope.available_colors = label_service.get_available_colors();

    $scope.initialize_new_label = function() {   
        $scope.new_label.color = "gray";
        $scope.new_label.label = "default";
    };

    $scope.create_new_label = function(new_label){
        label_service.create_label(new_label).then(
            function(data){
                //promise completed successfully
                var createdLabel = data.label;
                createdLabel.is_applied = false;
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
    }

    $scope.toggle_add = function(label){
        if (label.is_checked_remove && label.is_checked_add) {
            label.is_checked_remove = false;
        }
    }
    $scope.toggle_remove = function(label){
        if (label.is_checked_remove && label.is_checked_add) {
            label.is_checked_add = false;
        }
    }



    $scope.done = function () {

        var addLabels = [];
        var removeLabels = [];

        var len = $scope.labels.length;
        for (var index=0; index<len; index++){
            var label = $scope.labels[index];
            if (label.is_checked_add){
                addLabels.push(label.id);
            } else if (label.is_checked_remove) {
                removeLabels.push(label.id);
            }
        }

        label_service.update_building_labels(addLabels, removeLabels, search).then(
            function(data){  
                var msg = data.num_buildings_updated.toString() + " building labels updated." 
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

    $scope.cancel = function () {
        //don't do anything, just close modal.
        $uibModalInstance.dismiss('cancel');
    };


    $scope.initialize_new_label();
}]);
