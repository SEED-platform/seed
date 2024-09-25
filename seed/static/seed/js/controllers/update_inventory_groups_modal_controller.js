angular.module('SEED.controller.update_inventory_groups_modal', [])
  .controller('update_inventory_groups_modal_controller', [
    '$scope',
    '$log',
    '$uibModalInstance',
    'ah_service',
    'inventory_group_service',
    'organization_service',
    'user_service',
    'inventory_ids',
    'inventory_type',
    'org_id',
    'Notification',
    function (
      $scope,
      $log,
      $uibModalInstance,
      ah_service,
      inventory_group_service,
      organization_service,
      user_service,
      inventory_ids,
      inventory_type,
      org_id,
      notification
    ) {
      $scope.inventory_ids = inventory_ids;
      $scope.inventory_type = inventory_type;
      $scope.org_id = org_id;
      organization_service.get_lowest_common_ancestor(org_id, inventory_type, inventory_ids).then((response) => {
        console.log("TODO review")
        $scope.lowest_common_ancestor = response.data
        new_group.access_level_instance = response.data.id
      });
      // keep track of status of service call
      $scope.loading = false;

      // An array of all available groups in the system.
      // These group objects should have the has_member property set so
      // the modal can show the Remove button if necessary. (Populated
      // during init function below.)
      $scope.inventory_groups = [];

      $scope.new_group = {};
     

      /* Initialize the group props for a 'new' group */
      $scope.initialize_new_group = () => {
        $scope.new_group = {
          organization: $scope.org_id,
          inventory_type: $scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot',
          name: '',
          access_level_instance: user_service.get_access_level_instance().id
        };
      };

      /* Create a new group based on user input */
      $scope.submitNewGroupForm = (form) => {
        $scope.createdLabel = null;
        if (form.$invalid) return;
        inventory_group_service.new_group($scope.new_group).then(
          (data) => {
            // promise completed successfully
            const createdGroup = data.data;
            createdGroup.is_checked_add = false;
            $scope.newGroupForm.$setPristine();
            $scope.inventory_groups.unshift(createdGroup);
            $scope.initialize_new_group();
          },
          (data) => {
            // reject promise
            // group name already exists
            if (data.message === 'group already exists') {
              alert('group already exists');
            } else {
              alert('error creating new group');
            }
          }
        );
      };

      $scope.add_permission = (group) => {
        // const condition1 = [$scope.inventory_ids.length === 1 && group.member_list.length]
        if ($scope.lowest_common_ancestor) {
          console.log("TODO all must be same ali")
          const x = group.access_level_instance_data.lft > $scope.lowest_common_ancestor.lft && group.access_level_instance_data.rgt < $scope.lowest_common_ancestor.rgt
          return x
        }
        return false
      }

      /* Toggle the add button for a group */
      $scope.toggle_add = (group) => {
        if (group.is_checked_remove && group.is_checked_add) {
          group.is_checked_remove = false;
        }
      };

      /* Toggle the remove button for a group */
      $scope.toggle_remove = (group) => {
        if (group.is_checked_remove && group.is_checked_add) {
          group.is_checked_add = false;
        }
      };

      $scope.modified = () => Boolean(_.filter($scope.inventory_groups, 'is_checked_add').length || _.filter($scope.inventory_groups, 'is_checked_remove').length);

      /* User has indicated 'Done' so perform selected group operations */
      $scope.done = () => {
        const addGroupIDs = _.chain($scope.inventory_groups).filter('is_checked_add').map('id').value()
          .sort();
        const removeGroupIDs = _.chain($scope.inventory_groups).filter('is_checked_remove').map('id').value()
          .sort();

        if (inventory_type === 'properties') {
          inventory_group_service.update_inventory_groups(addGroupIDs, removeGroupIDs, inventory_ids, 'property').then((data) => {
            if (data.num_updated === 1) {
              notification.primary(`${data.num_updated} property updated.`);
            } else {
              notification.primary(`${data.num_updated} properties updated.`);
            }
            $uibModalInstance.close();
          }, (data, status) => {
            $log.error('error:', data, status);
          });
        } else if (inventory_type === 'taxlots') {
          inventory_group_service.update_inventory_groups(addGroupIDs, removeGroupIDs, inventory_ids, 'tax_lot').then((data) => {
            if (data.num_updated === 1) {
              notification.primary(`${data.num_updated} tax lot updated.`);
            } else {
              notification.primary(`${data.num_updated} tax lots updated.`);
            }
            $uibModalInstance.close();
          }, (data, status) => {
            $log.error('error:', data, status);
          });
        }
      };

      /* User has cancelled dialog */
      $scope.cancel = () => {
        $uibModalInstance.dismiss('cancel');
      };

      /* init: Gets the list of groups. Sets up new group object. */
      const init = () => {
        $scope.initialize_new_group();
        $scope.loading = true;
        inventory_group_service.get_groups_for_inventory(inventory_type, inventory_ids).then((groups) => {
          $scope.inventory_groups = [];
          groups.forEach((group) => {
            if (group.organization === $scope.org_id &&
                group.inventory_type === ($scope.inventory_type === 'properties' ? 'Property' : 'Tax Lot')) {
              $scope.inventory_groups.push(group);
            }
          });
          $scope.loading = false;
        });
      };
      init();
    }]);
