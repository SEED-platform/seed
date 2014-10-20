/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.edit_label_modal', [])
.controller('edit_label_modal_ctrl', [
  '$scope',
  '$modalInstance',
  'labels',
  'project_service',
  function ($scope, $modalInstance, labels, project_service) {
    $scope.labels = labels;
    $scope.label_modal = {};
    $scope.label_modal.color = "gray";
    $scope.label_modal.label = "default";
    $scope.available_colors = project_service.get_available_colors();
    $scope.modal = {};
    $scope.modal.label = {};
    $scope.modal.label.state = "create";


    $scope.initialize_label_modal = function() {
        $scope.label_modal.color = "gray";
        $scope.label_modal.label = "default";
        $scope.label_modal.name = "";
        $scope.modal.label.state = "create";
    };

    $scope.add_label = function(label) {
        project_service.add_label(label).then(function(data){
            // resolve promise
            get_labels();
            $scope.initialize_label_modal();
        });
    };

    $scope.delete_label = function(label) {
        project_service.delete_label(label).then(function(data){
            // resolve promise
            get_labels();
        });
    };

    $scope.edit_label = function(label) {
        $scope.label_modal = angular.copy(label);
        $scope.modal.label.state = 'edit';
    };

    $scope.update_label = function(label) {
        project_service.update_label(label).then(function(data){
            // resolve promise
            get_labels();
            $scope.initialize_label_modal();
        });
    };
    var get_labels = function(building) {
        // gets all labels for an org user
        project_service.get_labels().then(function(data) {
            // resolve promise
            $scope.labels = data.labels;
        });
    };


    $scope.close = function () {
        $modalInstance.close();
    };

    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };


    $scope.initialize_label_modal();
}]);
