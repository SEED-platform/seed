/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.email_templates_modal', [])
  .controller('email_templates_modal_controller', [
    '$scope',
    'postoffice_service',
    '$uibModalInstance',
    'action',
    'data',
    'org_id',
    function (
      $scope,
      postoffice_service,
      $uibModalInstance,
      action,
      data,
      org_id
    ) {
      $scope.action = action;
      $scope.data = data;
      $scope.org_id = org_id;

      $scope.rename_template = function () {
        if (!$scope.disabled()) {
          var id = $scope.data.id;
          var template = _.omit($scope.data, 'id');
          template.name = $scope.newName;
          postoffice_service.update_template(id, template, $scope.org_id).then(function (result) {
            $uibModalInstance.close(result.name);
          }).catch(function () {
            $uibModalInstance.dismiss();
          });
        }
      };

      $scope.remove_template = function () {
        postoffice_service.remove_template($scope.data.id, $scope.org_id).then(function () {
          $uibModalInstance.close();
        }).catch(function () {
          $uibModalInstance.dismiss();
        });
      };

      $scope.new_template = function () {
        if (!$scope.disabled()) {
          postoffice_service.new_template({
            name: $scope.newName,
            organization_id: $scope.org_id
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
