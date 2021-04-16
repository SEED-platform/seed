/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.members', [])
  .controller('members_controller', [
    '$scope',
    '$uibModal',
    'users_payload',
    'organization_payload',
    'auth_payload',
    'auth_service',
    'organization_service',
    'user_profile_payload',
    'urls',
    function (
      $scope,
      $uibModal,
      users_payload,
      organization_payload,
      auth_payload,
      auth_service,
      organization_service,
      user_profile_payload,
      urls
    ) {
      $scope.ownerRoles = [
        'owner',
        'member',
        'viewer'
      ];
      $scope.memberRoles = [
        'member',
        'viewer'
      ];
      $scope.users = users_payload.users;
      $scope.org = organization_payload.organization;
      $scope.filter_params = {};
      $scope.auth = auth_payload.auth;
      $scope.user_profile = user_profile_payload;

      /**
       * remove_member: removes a user from the org
       *
       * @param {obj} user The user to be removed
       */
      $scope.remove_member = function (user) {
        organization_service.remove_user(user.user_id, $scope.org.id).then(function () {
          organization_service.get_organization_users({org_id: $scope.org.id}).then(function (data) {
            $scope.users = data.users;
            init();
          });
        }).catch(function (response) {
          $scope.$emit('app_error', response);
        });
      }

      /**
       * saves the changed role for the user
       * @param  {obj} user
       */
      $scope.update_role = function (user) {
        organization_service.update_role(user.user_id, $scope.org.id, user.role)
          .then(function (data) {
            refreshRoleStatus();
          })
          .catch(function (data) {
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
       * reset_all_passwords triggers a reset password email for all users
       */
      $scope.reset_all_passwords = function (confirm_message = "Really reset all passwords?  This will sign you out of SEED.") {
        if (confirm(confirm_message)) {
          organization_service.reset_all_passwords($scope.org.id);
          window.location.href = '/accounts/login/?next=' + window.location.pathname + window.location.hash;
        }
      };

      $scope.can_edit = function (user) {
        // Superusers can edit any user's role except for the org owner if there is only one
        if ($scope.auth.requires_superuser && !($scope.only_one_owner && user.role === 'owner')) {
          return 'owner';
        }
        // Owners can edit all roles except their own if they are the only owner
        if ($scope.auth.requires_owner && !($scope.only_one_owner && user.email === $scope.user_profile.email)) {
          return 'owner';
        }
        // Members can only edit their own role, and only to "viewer"
        if (!$scope.auth.requires_owner && $scope.auth.requires_member && user.email === $scope.user_profile.email) {
          return 'member';
        }
        return 'none';
      }

      function refreshRoleStatus(auth_refresh = true) {
        $scope.only_one_owner = (_.chain($scope.users)
          .filter(['role', 'owner'])
          .size()
          .value() === 1);

        if (auth_refresh) {
          auth_service.is_authorized($scope.org.id, ['can_invite_member', 'can_remove_member', 'requires_owner', 'requires_member', 'requires_superuser'])
            .then(function (data) {
              $scope.auth = data.auth;
            });
        }
      }

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

        refreshRoleStatus(false);
      };
      init();

    }
  ]);
