/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('SEED.controller.inventory_group_detail_dashboard', [])
  .controller('inventory_group_detail_dashboard_controller', [
    '$scope',
    '$state',
    '$stateParams',
    'cycles',
    'meter_types',
    'group',
    'inventory_group_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      cycles,
      meter_types,
      group,
      inventory_group_service
    ) {
      $scope.inventory_display_name = group.name;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.cycles = cycles.cycles;
      // only energy meter types for now (not water)
      $scope.meter_types = meter_types.energy;
      $scope.selectedCycle = $scope.cycles[0] ?? undefined;
      // cheating a bit here and setting the default type to district chilled water.
      // could be electricity instead
      $scope.selectedMeterType = 'District Chilled Water';

      $scope.sankey_data = {};
      $scope.sankey_no_data_message = null;
      inventory_group_service.get_dashboard_info($scope.group_id, $scope.selectedCycle.id).then((data) => { $scope.data = data; });

      $scope.changeCycle = () => {
        inventory_group_service.get_dashboard_info($scope.group_id, $scope.selectedCycle.id)
          .then((data) => {
            $scope.data = data;
            // update sankey
            $scope.updateSankey();
          });
      };

      $scope.changeMeterType = () => {
        console.log('Changing Sankey to: ', $scope.selectedMeterType);
        $scope.updateSankey();
      };

      $scope.updateSankey = () => {
        // clear chart data
        $scope.sankey_data = [];
        // pull in sankey data based on the meter type
        inventory_group_service.get_sankey_data($scope.group_id, $scope.selectedCycle.id, $scope.selectedMeterType)
          .then((data) => {
            $scope.sankey_data = data;
            if ($scope.sankey_data.length === 0) {
              $scope.sankey_no_data_message = 'No data available for the selected meter type and cycle.';
            } else {
              $scope.sankey_no_data_message = null;
            }

            // update the chart
            $scope.chart.data.datasets[0].data = $scope.sankey_data;
            $scope.chart.data.datasets[0].colorFrom = (c) => getColor(c.dataset.data[c.dataIndex].from);
            $scope.chart.data.datasets[0].colorTo = (c) => getColor(c.dataset.data[c.dataIndex].to);
            $scope.chart.update();
          })
          .catch((err) => {
            console.error('Error getting sankey data: ', err);
            $scope.sankey_no_data_message = 'Error retrieving data for the selected meter type and cycle.';
          });
      };

      const ctx = document.getElementById('chart').getContext('2d');
      const colors = {
        Oil: 'black',
        'Natural Gas': 'red',
        Coal: 'gray',
        'Fossil Fuels': 'slategray',
        Electricity: 'blue',
        Energy: 'orange'
      };

      // the y-order of nodes, smaller = higher
      const priority = {
        Oil: 1,
        'Natural Gas': 2,
        Coal: 3,
        'Fossil Fuels': 1,
        Electricity: 2,
        Energy: 1
      };

      const labels = {
        Oil: 'black gold (label changed)'
      };

      const getColor = (name) => colors[name] || 'green';

      $scope.chart = new Chart(ctx, {
        type: 'sankey',
        data: {
          datasets: [
            {
              data: [],
              priority,
              labels,
              borderWidth: 2,
              borderColor: 'black'
            }
          ]
        }
      });

      // initialize sankey w/ default cycle and meter type
      $scope.updateSankey();
    }]);
