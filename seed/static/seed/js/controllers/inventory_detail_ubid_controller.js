/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_ubid', [])
  .controller('inventory_detail_ubid_controller', [
    '$scope',
    '$stateParams',
    'inventory_payload',
    'organization_payload',
    function (
      $scope,
      $stateParams,
      inventory_payload,
      organization_payload
    ) {
      $scope.item_state = inventory_payload.state;
      $scope.org = organization_payload.organization;
      $scope.inventory_payload = inventory_payload;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.reload = false;

      // for nav
      $scope.inventory = {view_id: $stateParams.view_id};

      $scope.inventory_display_name = function (property_type) {
        let error = '';
        let field = property_type === 'property' ? $scope.org.property_display_field : $scope.org.taxlot_display_field;
        if (!(field in $scope.item_state)) {
          error = field + ' does not exist';
          field = 'address_line_1';
        }
        if (!$scope.item_state[field]) {
          error += `${error === '' ? '' : ' and default '}${field} is blank`;
        }
        $scope.inventory_name = $scope.item_state[field] ? $scope.item_state[field] : `(${error}) <i class="glyphicon glyphicon-question-sign" title="This can be changed from the organization settings page."></i>`;
      };

      $scope.$on('reload', () => {
        // pass to the map controller
        $scope.reload = true;
      });
    }
  ]);
