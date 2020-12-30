/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_analyses', [])
  .controller('inventory_detail_analyses_controller', [
    '$state',
    '$scope',
    '$stateParams',
    '$uibModal',
    '$window',
    'inventory_service',
    'inventory_payload',
    'analyses_payload',
    'users_payload',
    'organization_payload',
    'urls',
    '$log',
    'analyses_service',
    'Notification',
    'uploader_service',
    function (
      $state,
      $scope,
      $stateParams,
      $uibModal,
      $window,
      inventory_service,
      inventory_payload,
      analyses_payload,
      users_payload,
      organization_payload,
      urls,
      $log,
      analyses_service,
      Notification,
      uploader_service,
    ) {
      $scope.item_state = inventory_payload.state;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.view_id = $stateParams.view_id;
      $scope.org = organization_payload.organization;
      $scope.users = users_payload.users;
      $scope.analyses = analyses_payload.analyses;
      $scope.inventory = {
        view_id: $stateParams.view_id
      };

      refresh_analyses = function() {
        analyses_service.get_analyses_for_canonical_property(inventory_payload.property.id)
        .then(function(data) {
          $scope.analyses = data.analyses
        })
      }

      $scope.start_analysis = function(analysis_id) {
        analysis = $scope.analyses.find(function(a) { return a.id === analysis_id })
        analysis.status = 'Starting...'

        analyses_service.start_analysis(analysis_id)
        .then(function (result) {
          if (result.status === 'success') {
            Notification.primary('Analysis started')
            refresh_analyses()
            uploader_service.check_progress_loop(result.progress_key, 0, 1, function() {
              refresh_analyses()
            }, function() {
              refresh_analyses()
            }, {})
          } else {
            Notification.error('Failed to start analysis: ' + result.message)
          }
        })
      }

      $scope.stop_analysis = function(analysis_id) {
        analysis = $scope.analyses.find(function(a) { return a.id === analysis_id })
        analysis.status = 'Stopping...'

        analyses_service.stop_analysis(analysis_id)
        .then(function (result) {
          if (result.status === 'success') {
            Notification.primary('Analysis stopped')
            refresh_analyses()
          } else {
            Notification.error('Failed to stop analysis: ' + result.message)
          }
        })
      }

      $scope.open_analysis_modal = function () {
        $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/inventory_detail_analyses_modal.html',
          controller: 'inventory_detail_analyses_modal_controller',
          resolve: {
            inventory_ids: function () {
              return [$scope.inventory.view_id];
            },
          //   meters: ['$stateParams', 'user_service', 'meter_service', function ($stateParams, user_service, meter_service) {
          //   var organization_id = user_service.get_organization().id;
          //   return meter_service.get_meters($stateParams.view_id, organization_id);
          // }],
          }
        }).result.then(function(data) {
          if (data) {
            refresh_analyses()
            uploader_service.check_progress_loop(data.progress_key, 0, 1, function() {
              refresh_analyses()
            }, function() {
              refresh_analyses()
            }, {})
          }
        });
      };
    }]);
