/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_analyses', []).controller('inventory_detail_analyses_controller', [
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
  'views_payload',
  'urls',
  '$log',
  'analyses_service',
  'Notification',
  'uploader_service',
  'cycle_service',
  // eslint-disable-next-line func-names
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
    views_payload,
    urls,
    $log,
    analyses_service,
    Notification,
    uploader_service,
    cycle_service
  ) {
    $scope.item_state = inventory_payload.state;
    $scope.inventory_type = $stateParams.inventory_type;
    $scope.view_id = $stateParams.view_id;
    $scope.cycle = inventory_payload.cycle;
    // WARNING: $scope.org is used by "child" controller - analysis_details_controller
    $scope.org = organization_payload.organization;
    $scope.users = users_payload.users;
    $scope.analyses = analyses_payload.analyses;
    $scope.inventory = {
      view_id: $stateParams.view_id
    };
    $scope.tab = 0;
    $scope.cycle = inventory_payload.cycle;

    views_payload = $scope.inventory_type === 'properties' ? views_payload.property_views : views_payload.taxlot_views;
    $scope.views = views_payload
      .map(({ id, cycle }) => ({
        view_id: id,
        cycle_name: cycle.name
      }))
      .sort((a, b) => a.cycle_name.localeCompare(b.cycle_name));
    $scope.selected_view = $scope.views.find(({ view_id }) => view_id === $scope.inventory.view_id);
    $scope.changeView = () => {
      $state.go('inventory_detail_analyses', { inventory_type: $scope.inventory_type, view_id: $scope.selected_view.view_id });
    };

    const refresh_analyses = () => {
      analyses_service.get_analyses_for_canonical_property(inventory_payload.property.id).then((data) => {
        $scope.analyses = analyses_payload.analyses.filter((analysis) => analysis.cycles.includes($scope.cycle.id));
        $scope.analyses_by_type = {};
        for (const analysis in $scope.analyses) {
          if (!$scope.analyses_by_type[$scope.analyses[analysis].service]) {
            $scope.analyses_by_type[$scope.analyses[analysis].service] = [];
          }
          $scope.analyses_by_type[$scope.analyses[analysis].service].push($scope.analyses[analysis]);
        }
      });
    };
    refresh_analyses();

    $scope.start_analysis = (analysis_id) => {
      const analysis = $scope.analyses.find((a) => a.id === analysis_id);
      analysis.status = 'Starting...';

      analyses_service.start_analysis(analysis_id).then((result) => {
        if (result.status === 'success') {
          Notification.primary('Analysis started');
          refresh_analyses();
          uploader_service.check_progress_loop(
            result.progress_key,
            0,
            1,
            () => {
              refresh_analyses();
            },
            () => {
              refresh_analyses();
            },
            {}
          );
        } else {
          Notification.error(`Failed to start analysis: ${result.message}`);
        }
      });
    };

    $scope.stop_analysis = (analysis_id) => {
      const analysis = $scope.analyses.find((a) => a.id === analysis_id);
      analysis.status = 'Stopping...';

      analyses_service.stop_analysis(analysis_id).then((result) => {
        if (result.status === 'success') {
          Notification.primary('Analysis stopped');
          refresh_analyses();
        } else {
          Notification.error(`Failed to stop analysis: ${result.message}`);
        }
      });
    };

    $scope.delete_analysis = (analysis_id) => {
      const analysis = $scope.analyses.find((a) => a.id === analysis_id);
      analysis.status = 'Deleting...';

      analyses_service.delete_analysis(analysis_id).then((result) => {
        if (result.status === 'success') {
          Notification.primary('Analysis deleted');
          refresh_analyses();
        } else {
          Notification.error(`Failed to delete analysis: ${result.message}`);
        }
      });
    };

    $scope.inventory_display_name = (property_type) => {
      let error = '';
      let field = property_type === 'property' ? $scope.org.property_display_field : $scope.org.taxlot_display_field;
      if (!(field in $scope.item_state)) {
        error = `${field} does not exist`;
        field = 'address_line_1';
      }
      if (!$scope.item_state[field]) {
        error += `${(error === '' ? '' : ' and default ') + field} is blank`;
      }
      $scope.inventory_name = $scope.item_state[field] ?
        $scope.item_state[field] :
        `(${error}) <i class="glyphicon glyphicon-question-sign" title="This can be changed from the organization settings page."></i>`;
    };

    $scope.open_analysis_modal = () => {
      $uibModal
        .open({
          templateUrl: `${urls.static_url}seed/partials/inventory_detail_analyses_modal.html`,
          controller: 'inventory_detail_analyses_modal_controller',
          resolve: {
            inventory_ids: () => [$scope.inventory.view_id],
            cycles: () => cycle_service.get_cycles().then((result) => result.cycles),
            current_cycle: () => $scope.cycle
          }
        })
        .result.then((data) => {
          if (data) {
            refresh_analyses();
            uploader_service.check_progress_loop(
              data.progress_key,
              0,
              1,
              () => {
                refresh_analyses();
              },
              () => {
                refresh_analyses();
              },
              {}
            );
          }
        });
    };
    $scope.has_children = (value) => typeof value === 'object';
  }
]);
