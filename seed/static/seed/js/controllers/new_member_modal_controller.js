/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.new_member_modal', [])
  .controller('new_member_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'organization',
    'user_service',
    '$timeout',
    '$translate',
    function (
      $scope,
      $uibModalInstance,
      organization,
      user_service,
      $timeout,
      $translate
    ) {
      $scope.roles = [{
        name: $translate.instant('Owner'),
        value: 'owner'
      }, {
        name: $translate.instant('Member'),
        value: 'member'
      }, {
        name: $translate.instant('Viewer'),
        value: 'viewer'
      }];
      $scope.user = {
        organization,
        role: $scope.roles[1]
      };

      /**
       * adds a user to the org
       */
      $scope.submit_form = function () {
        // make `role` a string
        const u = _.cloneDeep($scope.user);
        u.role = u.role.value;

        user_service.add(u).then(function () {
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
