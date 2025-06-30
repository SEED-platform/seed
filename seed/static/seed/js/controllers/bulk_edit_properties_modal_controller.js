/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.bulk_edit_properties_modal', [])
  .controller('bulk_edit_properties_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'cycle_service',
    'inventory_service',
    'property_view_ids',
    'compliance_cycle_year_column',
    'include_in_total_denominator_column',
    'exclude_from_plan_column',
    'require_in_plan_column',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      cycle_service,
      inventory_service,
      property_view_ids,
      compliance_cycle_year_column,
      include_in_total_denominator_column,
      exclude_from_plan_column,
      require_in_plan_column
    ) {
      // console.log(property_view_ids);
      // console.log(compliance_cycle_year_column);
      // console.log(include_in_total_denominator_column);
      // console.log(exclude_from_plan_column);
      // console.log(require_in_plan_column);

      $scope.compliance_cycle_year_column_new_value = null;
      $scope.include_in_total_denominator_column_new_value = null;
      $scope.exclude_from_plan_column_new_value = null;
      $scope.require_in_plan_column_new_value = null;

      $scope.cycles = [1, 2, 3, 4];

      $scope.update_properties = () => {
        // console.log('property_view_ids', property_view_ids);
        // console.log('compliance_cycle_year_column', compliance_cycle_year_column?.id, $scope.compliance_cycle_year_column_new_value);
        // console.log('include_in_total_denominator_column', include_in_total_denominator_column?.id, $scope.include_in_total_denominator_column_new_value);
        // console.log('exclude_from_plan_column', exclude_from_plan_column?.id, $scope.exclude_from_plan_column_new_value);
        // console.log('require_in_plan_column', require_in_plan_column?.id, $scope.require_in_plan_column_new_value);

        const update_patch = {
          [compliance_cycle_year_column?.id]: $scope.compliance_cycle_year_column_new_value,
          [include_in_total_denominator_column?.id]: $scope.include_in_total_denominator_column_new_value == null ? null : $scope.include_in_total_denominator_column_new_value === 'true',
          [exclude_from_plan_column?.id]: $scope.exclude_from_plan_column_new_value == null ? null : $scope.exclude_from_plan_column_new_value === 'true',
          [require_in_plan_column?.id]: $scope.require_in_plan_column_new_value == null ? null : $scope.require_in_plan_column_new_value === 'true'
        };
        // console.log(update_patch);
        Object.keys(update_patch).forEach((key) => {
          if (update_patch[key] == null) {
            delete update_patch[key];
          }
        });
        delete update_patch[undefined];

        // console.log(update_patch);

        inventory_service.update_property_states(property_view_ids, update_patch).then(() => {
          $state.reload();
          $uibModalInstance.dismiss();
        });
      };

      $scope.close = () => {
        $uibModalInstance.dismiss();
      };
    }
  ]);
