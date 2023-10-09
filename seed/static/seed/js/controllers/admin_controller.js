/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.admin', []).controller('admin_controller', [
  '$scope',
  '$log',
  '$uibModal',
  'user_service',
  'organization_service',
  'column_mappings_service',
  'uploader_service',
  'auth_payload',
  'organizations_payload',
  'user_profile_payload',
  'users_payload',
  'Notification',
  '$window',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $log,
    $uibModal,
    user_service,
    organization_service,
    column_mappings_service,
    uploader_service,
    auth_payload,
    organizations_payload,
    user_profile_payload,
    users_payload,
    Notification,
    $window
  ) {
    $scope.is_superuser = auth_payload.auth.requires_superuser;
    $scope.user = {};
    $scope.temp_users = [];
    $scope.org = {
      users: users_payload.users
    };
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
    $scope.username = `${user_profile_payload.first_name} ${user_profile_payload.last_name}`;

    const update_alert = (is_ok, message) => {
      $scope.alert.show = true;
      $scope.alert.css = is_ok ? $scope.alert.bootstrap_class.ok : $scope.alert.bootstrap_class.error;
      $scope.alert.message = message;
    };
    $scope.update_alert = update_alert;

    $scope.org_form.reset = () => {
      $scope.org.user_email = '';
      $scope.org.name = '';
    };
    $scope.org_form.add = (org) => {
      organization_service
        .add(org)
        .then(() => {
          get_organizations().then(() => {
            $scope.$emit('organization_list_updated');
          });
          update_alert(true, `Organization ${org.name} created`);
        })
        .catch((response) => {
          update_alert(false, `error creating organization: ${response.data.message}`);
        });
    };
    $scope.user_form.add = (user) => {
      user_service
        .add(user)
        .then((data) => {
          let alert_message = `User ${user.email} created and added`;
          if (data.org_created) {
            alert_message = `${alert_message} as head of new org ${data.org}`;
          } else {
            alert_message = `${alert_message} to existing org ${data.org}`;
          }

          update_alert(true, alert_message);
          get_users();
          get_organizations().then(() => {
            $scope.$emit('organization_list_updated');
          });
          $scope.user_form.reset();
        })
        .catch((response) => {
          update_alert(false, `error creating user: ${response.data.message}`);
        });
    };
    $scope.org_form.not_ready = () => _.isUndefined($scope.org.email) || organization_exists($scope.org.name);

    var organization_exists = (name) => {
      const orgs = _.map($scope.org_user.organizations, (org) => org.name.toLowerCase());
      return _.includes(orgs, name.toLowerCase());
    };

    $scope.user_form.not_ready = () => !$scope.user.organization && !$scope.user.org_name;

    $scope.user_form.reset = () => {
      $scope.user = {};
    };

    $scope.org_form.reset();

    $scope.user_form.reset();

    var get_users = () => {
      user_service.get_users().then((data) => {
        $scope.org.users = data.users;
      });
    };

    const process_organizations = (data) => {
      $scope.org_user.organizations = data.organizations;
      _.forEach($scope.org_user.organizations, (org) => {
        org.total_inventory = _.reduce(org.cycles, (sum, cycle) => sum + cycle.num_properties + cycle.num_taxlots, 0);
      });
    };

    var get_organizations = () => organization_service.get_organizations().then(process_organizations, (response) => {
      $log.log({ message: 'error from data call', status: response.status, data: response.data });
      update_alert(false, `error getting organizations: ${response.data.message}`);
    });

    $scope.get_organizations_users = (org) => {
      if (org) {
        organization_service
          .get_organization_users(org)
          .then((data) => {
            $scope.org_user.users = data.users;
          })
          .catch((response) => {
            $log.log({ message: 'error from data call', status: response.status, data: response.data });
            update_alert(false, `error getting organizations: ${response.data.message}`);
          });
      } else {
        $scope.org_user.users = [];
      }
    };

    $scope.org_user.add = () => {
      organization_service
        .add_user_to_org($scope.org_user)
        .then(() => {
          get_organizations().then(() => {
            $scope.$emit('organization_list_updated');
          });
          $scope.get_organizations_users($scope.org_user.organization);
          update_alert(true, `user ${$scope.org_user.user.email} added to organization ${$scope.org_user.organization.name}`);
        })
        .catch((response) => {
          $log.log({ message: 'error from data call', status: response.status, data: response.data });
          update_alert(false, `error adding user to organization: ${response.data.message}`);
        });
    };

    $scope.confirm_remove_user = (user, org_id) => {
      organization_service
        .remove_user(user.user_id, org_id)
        .then(() => {
          $scope.get_organizations_users($scope.org_user.organization);
          get_users();
          update_alert(true, `user ${user.email} removed from organization ${$scope.org_user.organization.name}`);
        })
        .catch((response) => {
          $log.log({ message: 'error from data call', status: response.status, data: response.data });
          update_alert(false, `error removing user from organization: ${response.data.message}`);
        });
    };

    $scope.confirm_column_mappings_delete = (org) => {
      const yes = confirm(`Are you sure you want to delete the '${org.name}' column mappings?  This will invalidate preexisting mapping review data`);
      if (yes) {
        $scope.delete_org_column_mappings(org);
      }
    };

    $scope.delete_org_column_mappings = (org) => {
      column_mappings_service.delete_all_column_mappings_for_org(org.org_id).then((data) => {
        if (data.delete_count === 0) {
          Notification.info('No column mappings exist.');
        } else if (data.delete_count === 1) {
          Notification.success(`${data.delete_count} column mapping deleted.`);
        } else {
          Notification.success(`${data.delete_count} column mappings deleted.`);
        }
      });
    };

    /**
     * confirm_inventory_delete: checks with the user before kicking off the delete task
     * for an org's inventory.
     */
    $scope.confirm_inventory_delete = (org) => {
      const yes = confirm(`Are you sure you want to PERMANENTLY delete '${org.name}'s properties and tax lots?`);
      if (yes) {
        $scope.delete_org_inventory(org);
      }
    };

    /**
     * delete_org_inventory: kicks off the delete task for an org's inventory.
     */
    $scope.delete_org_inventory = (org) => {
      org.progress = 0;
      organization_service.delete_organization_inventory(org.org_id).then((data) => {
        // resolve promise
        uploader_service.check_progress_loop(
          data.progress_key,
          0,
          1,
          () => {
            org.remove_message = 'success';
            get_organizations();
          },
          () => {
            // Do nothing
          },
          org
        );
      });
    };

    $scope.confirm_org_delete = (org) => {
      const yes = confirm(`Are you sure you want to PERMANENTLY delete the entire '${org.name}' organization?`);
      if (yes) {
        const again = confirm(`Deleting an organization is permanent. Confirm again to delete '${org.name}'`);
        if (again) {
          $scope.delete_org(org);
        }
      }
    };

    $scope.delete_org = (org) => {
      org.progress = 0;
      organization_service.delete_organization(org.org_id).then((data) => {
        uploader_service.check_progress_loop(
          data.progress_key,
          0,
          1,
          () => {
            org.remove_message = 'success';
            if (parseInt(org.id, 10) === parseInt(user_service.get_organization().id, 10)) {
              // Reload page if deleting current org.
              $window.location.reload();
            } else {
              get_organizations().then(() => {
                $scope.$emit('organization_list_updated');
              });
            }
          },
          () => {
            // Do nothing
          },
          org
        );
      });
    };

    process_organizations(organizations_payload);
  }
]);
