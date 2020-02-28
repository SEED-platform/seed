/*
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
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
    function (
      $scope,
      $uibModal,
      users_payload,
      organization_payload,
      auth_payload,
      organization_service,
      user_profile_payload,
      urls
    ) {
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
        if (user.number_of_orgs === 1) {
          var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/delete_user_modal.html',
            controller: 'delete_user_modal_controller',
            resolve: {
              user: function () {
                return user.email;
              }
            }
          });
          modalInstance.result.then(function () {
            confirm_remove_user(user);
          }).catch(function () {
            // Do nothing
          });
        } else {
          confirm_remove_user(user);
        }
      };

      function confirm_remove_user(user) {
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
