/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// called from open_edit_modal
angular.module('BE.seed.controller.edit_project_modal', [])
.controller('edit_project_modal_ctrl', [
  '$scope',
  '$modalInstance',
  'project',
  '$filter',
  '$location',
  'project_service',
  'create_project',
  function($scope, $modalInstance, project, $filter, $location, project_service, create_project) {
    $scope.project = angular.copy(project);
    $scope.project.deadline_date = $filter('date')($scope.project.deadline_date, 'yyyy-MM-dd') || null;
    $scope.project.end_date = $filter('date')($scope.project.end_date, 'yyyy-MM') || null;
    $scope.create_project_state = "create";

    $scope.ok = function () {
        if (create_project) {
            project_service.create_project($scope.project).then(
                function(data){
                    // resolve promise
                    console.log({data: data});
                    angular.extend($scope.project, data);
                    $scope.create_project_state = "success";
                },
                function(data, status){
                    $scope.create_project_error = true;
                    $scope.create_project_error_message = data.message;
                    console.log({data: data, status: status});
                });
        } else {
            project_service.update_project_name($scope.project).then(
                function(data){
                    // resolve promuse
                    $modalInstance.close($scope.project);
                },
                function(data, status){
                    // reject promise
                    // add alert here to signal update failed
                    // e.g. when project name is already taken within org
                    console.log({data: data, status: status});
                }
            );
        }
    };

    $scope.go_to_project = function() {
        $location.path('/projects/' + $scope.project.project_slug);
        $modalInstance.close($scope.project);
    };

    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };
    $scope.close = function () {
        $modalInstance.close($scope.project);
    };

    var init = function() {
        if (create_project) {
            $scope.modal_title = "Create a New Project";
            $scope.ok_button_text = "Create Project";
        } else {
            $scope.modal_title = "Edit Project";
            $scope.ok_button_text = "Save";
        }
    };
    init();
}]);
