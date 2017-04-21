/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.admin', [])
  .controller('admin_controller', [
    '$scope',
    '$state',
    'user_service',
    'organization_service',
    'column_mappings_service',
    'uploader_service',
    'user_profile_payload',
    'Notification',
    '$window',
    function ($scope, $state, user_service, organization_service, column_mappings_service, uploader_service, user_profile_payload, Notification, $window) {
      $scope.user = {};
      $scope.temp_users = [];
      $scope.org = {};
      $scope.org_user = {};
      $scope.org_form = {};
      $scope.user_form = {};
      $scope.alert = {
        show: false,
        message: 'congrats',
        bootstrap_class: {
          ok: 'alert-success',
          error: 'alert-danger'
        },
        css: 'alert-success'
      };
      $scope.username = user_profile_payload.first_name + ' ' + user_profile_payload.last_name;

      var update_alert = function (is_ok, message) {
        $scope.alert.show = true;
        $scope.alert.css = is_ok ? $scope.alert.bootstrap_class.ok : $scope.alert.bootstrap_class.error;
        $scope.alert.message = message;
      };
      $scope.update_alert = update_alert;

      $scope.org_form.reset = function () {
        $scope.org.user_email = '';
        $scope.org.name = '';
      };
      $scope.org_form.add = function (org) {
        organization_service.add(org).then(function (data) {
          // resolve promise
          $scope.org_form.invalid = false;
          get_organizations();
          $scope.$emit('organization_list_updated');
          update_alert(true, 'Organization ' + org.name + ' created');

        }, function (data) {
          // reject promise
          update_alert(false, 'error creating organization: ' + data.message);
        });
      };
      $scope.user_form.add = function (user) {
        user_service.add(user).then(function (data) {
          // resolve promise
          $scope.user_form.invalid = false;

          var alert_message = 'User ' + user.email + ' created and added';
          if (data.org_created) {
            alert_message = alert_message + ' as head of new org ' + data.org;
          } else {
            alert_message = alert_message + ' to existing org ' + data.org;
          }

          update_alert(true, alert_message);
          get_users();
          get_organizations();
          $scope.user_form.reset();

        }, function (data) {
          // reject promise
          update_alert(false, 'error creating user: ' + data.message);
        });
      };
      $scope.org_form.not_ready = function () {
        return _.isUndefined($scope.org.email);
      };

      $scope.user_form.reset = function () {
        $scope.user = {};
      };

      $scope.org_form.reset();

      $scope.user_form.reset();

      var get_users = function () {
        user_service.get_users().then(function (data) {
          // resolve promise
          $scope.org.users = data.users;
        });
      };

      var get_organizations = function () {
        organization_service.get_organizations().then(function (data) {
          // resolve promise
          $scope.org_user.organizations = data.organizations;
          _.forEach($scope.org_user.organizations, function (org) {
            org.total_inventory = _.reduce(org.cycles, function (sum, cycle) {
              return sum + cycle.num_properties + cycle.num_taxlots;
            }, 0);
          });
        }, function (data, status) {
          // reject promise
          console.log({message: 'error from data call', status: status, data: data});
          update_alert(false, 'error getting organizations. check console log ');
        });
      };

      $scope.get_organizations_users = function (org) {
        organization_service.get_organization_users(org).then(function (data) {
          // resolve promise
          $scope.org_user.users = data.users;
        }, function (data, status) {
          // reject promise
          console.log({message: 'error from data call', status: status, data: data});
          update_alert(false, 'error getting organizations. check console log ');
        });
      };

      $scope.org_user.add = function () {
        organization_service.add_user_to_org($scope.org_user).then(function (data) {
          // resolve promise
          $scope.get_organizations_users($scope.org_user.organization);
          update_alert(true, 'user ' + $scope.org_user.user.email + ' added to organization ' + $scope.org_user.organization.name);
        }, function (data, status) {
          // reject promise
          console.log({message: 'error from data call', status: status, data: data});
          update_alert(false, 'error adding user to organization: ' + data.message);
        });
      };

      $scope.org_user.remove_user = function (user_id, org_id) {
        organization_service.remove_user(user_id, org_id).then(function (data) {
          // resolve promise
          $scope.get_organizations_users($scope.org_user.organization);
          update_alert(true, 'user removed organization');
        }, function (data, status) {
          // reject promise
          console.log({message: 'error from data call', status: status, data: data});
          update_alert(false, 'error removing user from organization: ' + data.message);
        });
      };

      $scope.confirm_column_mappings_delete = function (org) {
        var yes = confirm('Are you sure you want to delete the \'' + org.name + '\' column mappings?  This will invalidate preexisting mapping review data');
        if (yes) {
          $scope.delete_org_column_mappings(org);
        }
      };

      $scope.delete_org_column_mappings = function (org) {
        column_mappings_service.delete_all_column_mappings_for_org(org.org_id).then(function (data) {
          if (data.delete_count == 0) {
            Notification.info('No column mappings exist.');
          } else if (data.delete_count == 1) {
            Notification.success(data.delete_count + ' column mapping deleted.');
          } else {
            Notification.success(data.delete_count + ' column mappings deleted.');
          }

        });
      };

      /**
       * confirm_inventory_delete: checks with the user before kicking off the delete task
       * for an org's inventory.
       */
      $scope.confirm_inventory_delete = function (org) {
        var yes = confirm('Are you sure you want to PERMANENTLY delete \'' + org.name + '\'s properties and tax lots?');
        if (yes) {
          $scope.delete_org_inventory(org);
        }
      };

      /**
       * delete_org_inventory: kicks off the delete task for an org's inventory.
       */
      $scope.delete_org_inventory = function (org) {
        org.progress = 0;
        organization_service.delete_organization_inventory(org.org_id)
          .then(function (data) {
            // resolve promise
            uploader_service.check_progress_loop(data.progress_key, 0, 1, function (data) {
                org.remove_message = 'success';
                get_organizations();
              }, function (data) {  //failure fn
                // Do nothing
              },
              org);
          });
      };

      $scope.confirm_org_delete = function (org) {
        var yes = confirm('Are you sure you want to PERMANENTLY delete the entire \'' + org.name + '\' organization?');
        if (yes) {
          var again = confirm('Deleting an organization is permanent. Confirm again to delete \'' + org.name + '\'');
          if (again) {
            $scope.delete_org(org);
          }
        }
      };

      $scope.delete_org = function (org) {
        org.progress = 0;
        organization_service.delete_organization(org.org_id)
          .then(function (data) {
            // resolve promise
            uploader_service.check_progress_loop(
              data.progress_key,  // key
              0, //starting prog bar percentage
              1.0,  // progress multiplier
              function (data) {  //success fn
                org.remove_message = 'success';
                if (parseInt(org.id) === parseInt(user_service.get_organization().id)) {
                  // Reload page if deleting current org.
                  $window.location.reload();
                } else {
                  get_organizations();
                  $scope.$emit('organization_list_updated');
                }
              }, function (data) {  //failure fn
                // Do nothing
              },
              org  // progress bar obj
            );
          });
      };

      var init = function () {
        get_users();
        get_organizations();
      };
      init();
    }]);
