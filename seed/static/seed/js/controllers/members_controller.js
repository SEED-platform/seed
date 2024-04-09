/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.members', []).controller('members_controller', [
  '$scope',
  '$uibModal',
  'users_payload',
  'organization_payload',
  'auth_payload',
  'auth_service',
  'organization_service',
  'user_profile_payload',
  'access_level_tree',
  'urls',
  'Notification',
  // eslint-disable-next-line func-names
  function ($scope, $uibModal, users_payload, organization_payload, auth_payload, auth_service, organization_service, user_profile_payload, access_level_tree, urls, Notification) {
    $scope.ownerRoles = ['owner', 'member', 'viewer'];
    $scope.memberRoles = ['member', 'viewer'];
    $scope.users = users_payload.users;
    $scope.org = organization_payload.organization;
    $scope.filter_params = {};
    $scope.auth = auth_payload.auth;
    $scope.user_profile = user_profile_payload;
    $scope.access_level_names = access_level_tree.access_level_names;
    $scope.user_id_being_edited = null;
    $scope.user_edits = {};

    /* Build out access_level_instances_by_depth recursively */
    const access_level_instances_by_depth = {};
    const calculate_access_level_instances_by_depth = (tree, depth = 1) => {
      if (tree === undefined) return;
      if (access_level_instances_by_depth[depth] === undefined) access_level_instances_by_depth[depth] = [];
      for (const ali of tree) {
        access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name });
        calculate_access_level_instances_by_depth(ali.children, depth + 1);
      }
    };
    calculate_access_level_instances_by_depth(access_level_tree.access_level_tree, 0);

    // Result of clicking "edit"
    $scope.begin_user_edits = (user) => {
      // set edited user and default edits
      $scope.user_id_being_edited = user.user_id;
      $scope.user_edits = {
        access_level_instance: {
          id: user.access_level_instance_id,
          name: user.access_level_instance_name
        },
        access_level: user.access_level,
        role: user.role
      };

      // the possible access_level_instances at that level
      const access_level_idx = $scope.access_level_names.findIndex((x) => x === $scope.user_edits.access_level);
      $scope.access_level_instances = access_level_instances_by_depth[access_level_idx];
    };

    // Result of pick a new al. sets ali options.
    $scope.change_access_level_instance_options = () => {
      const access_level_idx = $scope.access_level_names.findIndex((x) => x === $scope.user_edits.access_level);
      $scope.access_level_instances = access_level_instances_by_depth[access_level_idx];
      $scope.user_edits.access_level_instance = null;
    };

    // user user edits
    $scope.save_user_edits = () => {
      if ($scope.user_edits.access_level_instance === null) {
        Notification.error('Must select an ali.');
        return;
      }
      if ($scope.user_edits.role === 'owner' && $scope.user_edits.access_level !== $scope.access_level_names[0]) {
        Notification.error('Owners must be in the root.');
        return;
      }

      // update user
      const user = $scope.users.find((x) => x.user_id === $scope.user_id_being_edited);
      $scope.update_user(user, $scope.user_edits);

      user.role = $scope.user_edits.role;
      user.access_level_instance_id = $scope.user_edits.access_level_instance.id;
      user.access_level_instance_name = $scope.user_edits.access_level_instance.name;
      user.access_level = $scope.user_edits.access_level;

      // reset user edits
      $scope.user_id_being_edited = null;
      $scope.user_edits = {};
    };

    const refreshRoleStatus = (auth_refresh = true) => {
      $scope.only_one_owner = _.chain($scope.users).filter(['role', 'owner']).size().value() === 1;

      if (auth_refresh) {
        auth_service.is_authorized($scope.org.id, ['can_invite_member', 'can_remove_member', 'requires_owner', 'requires_member', 'requires_superuser']).then((data) => {
          $scope.auth = data.auth;
        });
      }
    };

    /**
     * update_user: updates a users role and access level instance
     */
    $scope.update_user = (user, user_edits) => {
      // 1. update role
      // 2. update ali
      organization_service.update_role(user.user_id, $scope.org.id, user_edits.role)
        .then(() => {
          refreshRoleStatus();
          return organization_service.update_ali(user.user_id, $scope.org.id, user_edits.access_level_instance.id);
        })
        .catch((data) => {
          $scope.$emit('app_error', data);
        });
    };

    $scope.cancel_user_edits = () => {
      $scope.user_id_being_edited = null;
      $scope.user_edits = {};
    };

    $scope.get_roles = (user) => {
      const user_in_root = user.access_level === $scope.org.access_level_names[0];
      if (user_in_root) {
        return ['owner', 'member', 'viewer'];
      }
      return ['member', 'viewer'];
    };

    /**
     * remove_member: removes a user from the org
     *
     * @param {obj} user The user to be removed
     */
    $scope.remove_member = (user) => {
      organization_service
        .remove_user(user.user_id, $scope.org.id)
        .then(() => {
          organization_service.get_organization_users({ org_id: $scope.org.id }).then((data) => {
            $scope.users = data.users;
            init();
          });
        })
        .catch((response) => {
          $scope.$emit('app_error', response);
        });
    };

    /**
     * new_member_modal open an AngularUI modal to add/invite a new member
     */
    $scope.new_member_modal = () => {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/new_member_modal.html`,
        controller: 'new_member_modal_controller',
        resolve: {
          organization: () => $scope.org,
          access_level_tree: () => access_level_tree.access_level_tree,
          level_names: () => access_level_tree.access_level_names
        }
      });
      modalInstance.result.then(
        () => {
          organization_service.get_organization_users({ org_id: $scope.org.id }).then((data) => {
            $scope.users = data.users;
            init();
          });
        },
        () => {
          // Do nothing
        }
      );
    };

    /**
     * reset_all_passwords triggers a reset password email for all users
     */
    $scope.reset_all_passwords = (confirm_message = 'Really reset all passwords?  This will sign you out of SEED.') => {
      if (confirm(confirm_message)) {
        organization_service.reset_all_passwords($scope.org.id);
        window.location.href = `/accounts/login/?next=${window.location.pathname}${window.location.hash}`;
      }
    };

    $scope.can_edit = (user) => {
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
    };

    /**
     * called on controller load and when users are refreshed
     *  - creates a name field for each user from first_name and last_name
     */
    const init = () => {
      $scope.user = $scope.users.map((u) => {
        u.first_name = u.first_name || '';
        u.last_name = u.last_name || '';
        u.name = `${u.first_name} ${u.last_name}`;
        return u;
      });

      refreshRoleStatus(false);
    };
    init();
  }
]);
