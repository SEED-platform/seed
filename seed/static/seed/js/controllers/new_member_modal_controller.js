/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.new_member_modal', [])
.controller('new_member_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'organization',
  'user_service',
  '$timeout',
  function ($scope, $uibModalInstance, organization, user_service, $timeout) {
    $scope.roles = [{
      name: 'Member',
      value: 'member'
    }, {
      name: 'Owner',
      value: 'owner'
    }, {
      name: 'Viewer',
      value: 'viewer'
    }];
    $scope.user = {};
    $scope.user.role = $scope.roles[0];
    $scope.user.organization = organization;

    /**
     * adds a user to the org
     */
    $scope.submit_form = function () {
      user_service.add($scope.user).then(function () {
        $uibModalInstance.close();
      }, function (data) {
        $scope.$emit('app_error', data);
      });
    };

    $scope.close = function () {
      $uibModalInstance.close();
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    $timeout(function () {
      angular.element('#newMemberFirstName').focus();
    }, 50);
  }]);
