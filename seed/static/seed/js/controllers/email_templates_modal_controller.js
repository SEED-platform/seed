// /**
//  * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
//  * :author
//  */
// angular.module('BE.seed.controller.group_modal', [])
//   .controller('group_modal_controller', [
//     '$scope', //from before
//     '$uibModalInstance', //?
//     'action', //new_group
//     'group_service', //from before
//     'inventory_service', //from before
//     //'settings_location',
//     'inventory_type', //new_group
//     'data', //new_group
//     'org_id', //new_group
//     function (
//       $scope,
//       $uibModalInstance,
//       action,
//       group_service,
//       inventory_service,
//       //settings_location,
//       inventory_type,
//       data,
//       org_id
//     ) {
//         $scope.action = action;
//         $scope.data = data;
//         $scope.org_id = org_id;
//         //$scope.settings_location = settings_location;
//         $scope.inventory_type = inventory_type;

//         $scope.rename_group = function () {
//           if (!$scope.disabled()) {
//             var id = $scope.data.id;
//             var group = _.omit($scope.data, 'id');
//             group.name = $scope.newName;
//             group_service.update_group(id, group).then(function (result) {
//               $uibModalInstance.close(result.name);
//             }).catch(function () {
//               $uibModalInstance.dismiss();
//             });
//           }
//         };

//         $scope.remove_group = function () {
//           group_service.remove_group($scope.data.id).then(function () {
//             $uibModalInstance.close();
//           }).catch(function () {
//             $uibModalInstance.dismiss();
//           });
//         };

//         //referenced from column_mapping_preset_modal_controller
//         $scope.new_group = function () { //called when modal button clicked
//           if (!$scope.disabled()) {
//             group_service.new_group({
//               name: $scope.newName,
//               inventory_type: $scope.inventory_type,
//               organization: $scope.org_id
//             }).then(function (result) {
//               $uibModalInstance.close(result.data);
//             });
//           }
//         };

//         $scope.disabled = function () {
//           if ($scope.action === 'rename') {
//             return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
//           } else if ($scope.action === 'new') {
//             return _.isEmpty($scope.newName);
//           }
//         };

//         $scope.cancel = function () {
//           $uibModalInstance.dismiss();
//         };
//   }]);





