/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
 angular.module('BE.seed.controller.filter_group_modal', [])
 .controller('filter_group_modal_controller', [
   '$scope',
   '$uibModalInstance',
   'filter_groups_service',
   'action',
   'data',
   function ($scope,
    $uibModalInstance,
    filter_groups_service,
    action,
    data
    ) {
     $scope.action = action;
     $scope.data = data;


     $scope.rename_filter_group = function () {
       if (!$scope.disabled()) {
         var id = $scope.data.id;
         var filter_group = _.omit($scope.data, 'id');
         filter_group.name = $scope.newName;
         filter_groups_service.update_filter_group(id, filter_group).then(function (result) {
           $uibModalInstance.close(result.name);
         }).catch(function () {
           $uibModalInstance.dismiss();
         });
       }
     };

     $scope.remove_filter_group = function () {
       filter_groups_service.remove_filter_group($scope.data.id).then(function () {
         $uibModalInstance.close();
       }).catch(function () {
         $uibModalInstance.dismiss();
       });
     };

     $scope.new_filter_group = function () {
       if (!$scope.disabled()) {
         filter_groups_service.new_filter_group({
           name: $scope.newName,
           query_dict: $scope.data.query_dict,
           inventory_type: $scope.data.inventory_type,
           labels: $scope.data.labels,
           label_logic: $scope.data.label_logic
         }).then(function (result) {
           $uibModalInstance.close(result);
         });
       }
     };

     $scope.disabled = function () {
       if ($scope.action === 'rename') {
         return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
       } else if ($scope.action === 'new') {
         return _.isEmpty($scope.newName);
       }
     };

     $scope.cancel = function () {
       $uibModalInstance.dismiss();
     };
   }]);
