/*
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.members', [])
  .controller('members_controller', [
    '$scope',
    '$uibModal',
    'users_payload',
    'organization_payload',
    'auth_payload',
    'organization_service',
    'user_profile_payload',
    'urls',
    function ($scope,
              $uibModal,
              users_payload,
              organization_payload,
              auth_payload,
              organization_service,
              user_profile_payload,
              urls) {
      $scope.roles = [
        'member', 'owner', 'viewer'
      ];
      $scope.users = users_payload.users;
      $scope.org = organization_payload.organization;
      $scope.filter_params = {};
      $scope.auth = auth_payload.auth;
      $scope.user_profile = user_profile_payload;

      $scope.is_last_owner = (_.chain($scope.users)
        .filter(['role', 'owner'])
        .size()
        .value() === 1);

      /**
       * remove_member: removes a user from the org, an owner can only be removed
       *                by another owner
       *
       * @param {obj} user The user to be removed
       */
      $scope.remove_member = function (user) {
        organization_service.remove_user(user.user_id, $scope.org.id).then(function () {
          organization_service.get_organization_users({org_id: $scope.org.id}).then(function (data) {
            $scope.users = data.users;
            init();
          });
        }, function (data) {
          $scope.$emit('app_error', data);
        });
      };

      /**
       * saves the changed role for the user
       * @param  {obj} user
       */
      $scope.update_role = function (user) {
        $scope.$emit('show_saving');
        organization_service.update_role(user.user_id, $scope.org.id, user.role)
          .then(function () {
            $scope.$emit('finished_saving');
          }, function (data) {
            $scope.$emit('app_error', data);
          });

      };

      /**
       * new_member_modal open an AngularUI modal to add/invite a new member
       */
      $scope.new_member_modal = function () {
        var modalInstance = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/new_member_modal.html',
          controller: 'new_member_modal_controller',
          resolve: {
            organization: function () {
              return $scope.org;
            }
          }
        });
        modalInstance.result.then(function () {
          organization_service.get_organization_users({org_id: $scope.org.id}).then(function (data) {
            $scope.users = data.users;
            init();
          });
        }, function () {
          // Do nothing
        });
      };

      /**
       * called on controller load and when users are refreshed
       *  - creates a name field for each user from first_name and last_name
       */
      var init = function () {
        $scope.user = $scope.users.map(function (u) {
          u.first_name = u.first_name || '';
          u.last_name = u.last_name || '';
          u.name = '' + u.first_name + ' ' + u.last_name;
          return u;
        });
      };
      init();

    }
  ]);
