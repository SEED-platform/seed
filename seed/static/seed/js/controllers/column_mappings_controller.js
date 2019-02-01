/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.column_mappings', [])
  .controller('column_mappings_controller', [
    '$scope',
    '$q',
    '$state',
    '$stateParams',
    'Notification',
    'column_mappings_service',
    'spinner_utility',
    'column_mappings',
    'organization_payload',
    'auth_payload',
    function ($scope,
              $q,
              $state,
              $stateParams,
              Notification,
              column_mappings_service,
              spinner_utility,
              column_mappings,
              organization_payload,
              auth_payload) {

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;

      $scope.state = $state.current;

      $scope.filter_params = {};

      $scope.property_count = column_mappings.property_count;
      $scope.taxlot_count = column_mappings.taxlot_count;
      $scope.column_mappings = column_mappings.column_mappings;

      $scope.delete_mapping = function (id) {
        column_mappings_service.delete_column_mapping_for_org($scope.org.id, id).then(function () {
          _.remove($scope.column_mappings, {id: id});
          if ($scope.inventory_type === 'properties') {
            --$scope.property_count;
          } else {
            --$scope.taxlot_count;
          }
        });
      };

      $scope.delete_all_mappings = function () {
        $scope.mappings_deleted = false;

        var promises = [];
        _.forEach($scope.column_mappings, function (mapping) {
          promises.push($scope.delete_mapping(mapping.id));
        });

        spinner_utility.show();
        $q.all(promises).then(function (results) {
          $scope.mappings_deleted = true;
          var totalChanged = results.length;
          Notification.success('Successfully deleted ' + totalChanged + ' column mapping' + (totalChanged === 1 ? '' : 's'));
        }, function (data) {
          $scope.$emit('app_error', data);
        }).finally(function () {
          spinner_utility.hide();
        });
      };

    }]);
