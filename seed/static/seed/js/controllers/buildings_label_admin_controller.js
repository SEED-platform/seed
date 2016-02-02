/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.label_admin', [])
.controller('label_admin_controller', [
    '$scope',
    '$log',
    'urls',
    'label_service',
    'simple_modal_service',
    'Notification',
function ($scope, $log, urls, label_service, simple_modal_service, notification) {
   
    $scope.available_colors = label_service.get_available_colors();
    $scope.labels = [];

    function initialize_new_label() {
        $scope.new_label = {color:"gray", label:"default", name:""};
    }

    $scope.showColor = function(label) {
        var selected = [];
        if(label.color) {
          selected = $filter('filter')($scope.available_colors, {value: label.color});
        }
        return selected.length ? selected[0].text : 'Not set';
    };




    /*  Take user input from New Label form and submit 
        to service to create a new label. */
    $scope.submitNewLabelForm = function (form){
        if (form.$invalid) {
            return;
        }
        label_service.create_label($scope.new_label).then(
            function(result){                  
                get_labels();
                var msg = "Created label " + getTruncatedName($scope.new_label.name); 
                notification.primary(msg);       
                initialize_new_label();     
                form.$setPristine(); 
            },
            function(message){
                $log.error("Error creating new label.", message);
            }
        );        
    };

  
    /* Checks for existing label name for inline edit form.
        Form assumes function will return a string if there's an existing label */
    $scope.checkEditLabelBeforeSave = function(data, currentLabelName){
        if (data === currentLabelName){
            return;
        }
        if (data===undefined || data==="") {
            return "Enter at least one character";
        }
        if(isLabelNameUsed(data)){
            return "That label name already exists";
        }         
    };

    function isLabelNameUsed(newLabelName) {
        var len = $scope.labels.length;
        for (var index=0;index<len;index++){
            var label = $scope.labels[index];
            if (label.name===newLabelName){
                return true;
            }
        }
        return false;
    }

    /* Submit edit when 'enter' is pressed */
    $scope.onEditLabelNameKeypress = function(e, form) {
        if (e.which === 13) {
            form.$submit();
        }
    };

  
    
    $scope.saveLabel = function(label, id, index) {
        //Don't update $scope.label until a 'success' from server
        angular.extend(label, {id: id});        
        label_service.update_label(label).then(
            function(data){
                var msg = "Label updated.";
                notification.primary(msg);    
                $scope.labels.splice(index, 1, data);
                $scope.label = data;
            },
            function(message){
                $log.error("Error saving label.", message);
            }
        );
    };


    $scope.deleteLabel = function(label, index) {
        var modalOptions = {
            type: "default",
            okButtonText: 'OK',
            cancelButtonText: 'Cancel',
            headerText: 'Confirm delete',
            bodyText: "Delete label \"" + label.name + "\" and remove it from all buildings it's been applied to?"
        };
        simple_modal_service.showModal(modalOptions).then(
            function(result){
                //user confirmed delete, so go ahead and do it.
                label_service.delete_label(label).then(
                    function(result){
                        //server deleted label, so remove it locally
                        $scope.labels.splice(index, 1);
                        var msg = "Deleted label " + getTruncatedName(label.name);
                        notification.primary(msg);
                    },
                    function(message){
                        $log.error("Error deleting label.", message);
                    }
                );               
            },
            function(message){
                //user doesn't want to delete after all.
        });
        
    };
  


   function get_labels(building) {
        // gets all labels for an org user
        label_service.get_labels().then(function(data) {
            // resolve promise
            $scope.labels = data.results;
        });
    }

    function getTruncatedName(name) {
        if (name && name.length>20){
             name = name.substr(0,20) + "...";
        }
        return name;       
    }
    
    function init(){
       get_labels();
       initialize_new_label();
    }
    init();

}
]);
