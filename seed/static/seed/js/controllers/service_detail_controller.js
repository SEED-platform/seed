/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.service_detail', []).controller('service_detail_controller', [
  '$scope',
  '$stateParams',
  '$uibModal',
  'urls',
  'organization_id',
  'service',
  'inventory_group_service',
  'service_service',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, $uibModal, urls, organization_id, service, inventory_group_service, service_service) {
    $scope.group_id = $stateParams.group_id;
    $scope.system_id = $stateParams.system_id;
    $scope.service_id = $stateParams.service_id;
    $scope.inventory_type = $stateParams.inventory_type;

    $scope.service = service;

    $scope.headers = ["Property", "Connected Via", "Connection Type", "Meter Data?"];

    $scope.open_service_meter_create_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/service_meter_creation_modal.html`,
        controller: 'service_meter_creation_modal_controller',
        resolve: {
          properties: inventory_group_service.get_group_properties(organization_id, $scope.group_id),
          organization_id: () => organization_id,
          service_service: () => service_service,
        }
      });
    };
  }
]);
