/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.project', [])
.controller('project_list_controller', [
  /*'$scope',
  '$http',
  'project_service',
  'urls',
  '$log',
  '$uibModal',
  'projects_payload',*/
  function (/*$scope, $http, project_service, urls, $log, $uibModal, projects_payload*/) {

    // $scope.autoFilter = true;
    // $scope.user = {};
    // $scope.user.projects = projects_payload.projects;
    // $scope.$on('projects_updated', function () {
    //   // get new list of projects
    //   get_projects();
    // });

    // $scope.delete_project = function (project) {
    //   if (confirm('Are you sure you want to PERMANENTLY delete the \'' + project.name + '\'\' project?')) {
    //     project_service.delete_project(project.slug).then(function () {
    //       // get new list of projects
    //       $scope.$emit('project_created');
    //       get_projects();
    //     });
    //   }
    // };

    // $scope.open_edit_modal = function (p) {
    //   $scope.the_project = p;
    //   var modalInstance = $uibModal.open({
    //     templateUrl: urls.static_url + 'seed/partials/edit_project_modal.html',
    //     controller: 'edit_project_modal_controller',
    //     resolve: {
    //       project: function () {
    //         return $scope.the_project;
    //       },
    //       create_project: _.constant(false)
    //     }
    //   });

    //   modalInstance.result.then(function (project) {
    //     $log.info(project);
    //     get_projects();
    //   }, function (message) {
    //     $log.info(message);
    //     $log.info('Modal dismissed at: ' + new Date());
    //   });
    // };

    // var get_projects = function () {
    //   project_service.get_projects().then(function (data) {
    //     $scope.user.projects = data.projects;
    //   });
    // };
  }]);
