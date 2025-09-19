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
    'group',
    'inventory_group_service',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $stateParams,
      cycles,
      group,
      inventory_group_service
    ) {
      $scope.inventory_display_name = group.name;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.group_id = $stateParams.group_id;
      $scope.cycles = cycles.cycles;
      $scope.selectedCycle = $scope.cycles[0] ?? undefined;
      $scope.data = {};
      inventory_group_service.get_dashboard_info($scope.group_id, $scope.selectedCycle.id).then((data) => { $scope.data = data; });

      $scope.changeCycle = () => {
        inventory_group_service.get_dashboard_info($scope.group_id, $scope.selectedCycle.id).then((data) => { $scope.data = data; });
      };

      var ctx = document.getElementById("chart").getContext("2d");
      var colors = {
        Oil: "black",
        Coal: "gray",
        "Fossil Fuels": "slategray",
        Electricity: "blue",
        Energy: "orange"
      };

      // the y-order of nodes, smaller = higher
      var priority = {
        Oil: 1,
        'Narural Gas': 2,
        Coal: 3,
        'Fossil Fuels': 1,
        Electricity: 2,
        Energy: 1
      };

      var labels = {
        Oil: 'black gold (label changed)'
      }

      function getColor(name) {
        return colors[name] || "green";
      }

      const data = [
    {
      "from": "system FTLB​  Chiller 3",
      "to": "system FTLB Plant​",
      "flow": null
    },
    {
      "from": "system FTLB​  Chiller 1​",
      "to": "system FTLB Plant​",
      "flow": null
    },
    {
      "from": "system FTLB​  Flat Plate HX​",
      "to": "system FTLB Plant​",
      "flow": null
    },
    {
      "from": "system FTLB​  Chiller 2",
      "to": "system FTLB Plant​",
      "flow": null
    },
    {
      "from": "system SERF​  HX1​",
      "to": "system SERF Plant​",
      "flow": null
    },
    {
      "from": "system SERF​  Chiller 3",
      "to": "system SERF Plant​",
      "flow": 7
    },
    {
      "from": "system SERF​  HX2",
      "to": "system SERF Plant​",
      "flow": null
    },
    {
      "from": "system SERF​  Chiller 4",
      "to": "system SERF Plant​",
      "flow": null
    },
    {
      "from": "system SERF​  Chiller 2​",
      "to": "system SERF Plant​",
      "flow": 3
    },
    {
      "from": "system FTLB Plant​",
      "to": "system “Infrastructure”​  (East Campus)​",
      "flow": null
    },
    {
      "from": "system SERF Plant​",
      "to": "system “Infrastructure”​  (East Campus)​",
      "flow": null
    },
    {
      "from": "system FTLB Plant​",
      "to": "system “Spine”​ (West Campus)​",
      "flow": null
    },
    {
      "from": "system “Spine”​ (West Campus)​",
      "to": "property 7",
      "flow": null
    },
    {
      "from": "system “Spine”​ (West Campus)​",
      "to": "property 8",
      "flow": null
    },
    {
      "from": "system “Spine”​ (West Campus)​",
      "to": "property 9",
      "flow": null
    },
    {
      "from": "system FTLB Plant​",
      "to": "property 10",
      "flow": null
    },
    {
      "from": "system “Infrastructure”​  (East Campus)​",
      "to": "property 11",
      "flow": null
    },
    {
      "from": "system “Infrastructure”​  (East Campus)​",
      "to": "property 11",
      "flow": null
    },
    {
      "from": "system “Infrastructure”​  (East Campus)​",
      "to": "property 12",
      "flow": null
    },
    {
      "from": "system SERF Plant​",
      "to": "property 13",
      "flow": 11
    },
    {
      "from": "system SERF Plant​",
      "to": "property 14",
      "flow": null
    }
  ];

      var chart = new Chart(ctx, {
        type: "sankey",
        data: {
          datasets: [
            {
              data: data.map(d => {
                return {...d, flow: Math.floor(Math.random() * 10)}
              }),
              priority,
              labels,
              colorFrom: (c) => getColor(c.dataset.data[c.dataIndex].from),
              colorTo: (c) => getColor(c.dataset.data[c.dataIndex].to),
              borderWidth: 2,
              borderColor: 'black'
            }
          ]
        }
      });
    }]);
