/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.derived_columns_admin', [])
  .controller('derived_columns_admin_controller', [
    '$scope',
    '$log',
    '$state',
    '$stateParams',
    'derived_columns_service',
    'Notification',
    'simple_modal_service',
    'auth_payload',
    'organization_payload',
    'derived_columns_payload',
    function (
      $scope,
      $log,
      $state,
      $stateParams,
      derived_columns_service,
      Notification,
      simple_modal_service,
      auth_payload,
      organization_payload,
      derived_columns_payload
    ) {

      $scope.auth = auth_payload.auth;
      $scope.org = organization_payload.organization;
      $scope.derived_columns = derived_columns_payload.derived_columns;

      // used to determine column sorting. 0 = no sort, 1 = ascending, 2 = descending
      $scope.column_sorting = 0;

      $scope.toggle_name_order_sort = function () {
        $scope.column_sorting = ($scope.column_sorting + 1) % 3
        if (0 == $scope.column_sorting) {
          $scope.derived_columns.sort((a, b) => (a.id > b.id) ? 1 : -1)
        } else if (1 == $scope.column_sorting) {
          $scope.derived_columns.sort((a, b) => (a.name > b.name) ? 1 : -1)
        } else {
          $scope.derived_columns.sort((a, b) => (a.name < b.name) ? 1 : -1)
        }
      };

      $scope.edit_derived_column = function(derived_column_id) {
        $state.go('organization_derived_column_editor', {organization_id: $scope.org.id, derived_column_id});
      }

      $scope.delete_derived_column = function(derived_column_id) {
        const derived_column = $scope.derived_columns.find(dc => dc.id == derived_column_id)

        const modalOptions = {
          type: 'default',
          okButtonText: 'Yes',
          cancelButtonText: 'Cancel',
          headerText: 'Are you sure?',
          bodyText: `You're about to permanently delete the derived column "${derived_column.name}". Would you like to continue?`
        }
        simple_modal_service.showModal(modalOptions).then(() => {
          //user confirmed, delete it
          derived_columns_service.delete_derived_column($scope.org.id, derived_column_id)
            .then(() => {
              Notification.success(`Deleted "${derived_column.name}"`)
              derived_columns_service.get_derived_columns($scope.org.id, $stateParams.inventory_type)
                .then(res => $scope.derived_columns = res.derived_columns)
                .catch(err => {
                  $log.error(err)
                  // try just refreshing the page...
                  location.reload()
                })
            })
            .catch(err => {
              $log.error(err)
              Notification.error(`Error attempting to delete "${derived_column.name}". Please refresh the page and try again.`)
            })
        }, () => {
          //user doesn't want to
        })
      }
    }
  ]);
