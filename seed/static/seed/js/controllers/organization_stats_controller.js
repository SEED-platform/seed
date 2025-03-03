/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.organization_stats', []).controller('organization_stats_controller', [
  '$scope',
  'all_columns',
  'organization_payload',
  'auth_payload',
  'statistics_payload',
  'statistics_service',
  'Notification',

  // eslint-disable-next-line func-names
  function ($scope, all_columns, organization_payload, auth_payload, statistics_payload, statistics_service, Notification) {
    $scope.fields = all_columns.columns;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;
    $scope.data_fetched = false;
    $scope.data = [];

    $scope.conf = {};
    if (statistics_payload.length > 0) {
      $scope.conf = statistics_payload[0];
    }

    // hardcoding these for now but we should make a service for them at some point
    $scope.electric_units = [
      'GJ',
      'kBtu',
      'kWh',
      'MBtu/MMBtu',
      'MWh'
    ];
    $scope.gas_units = [
      'GJ',
      'kBtu',
      'MBtu/MMBtu',
      'therms',
      'kWh',
      'kcf',
      'Mcf'
    ];
    $scope.area_units = ['ft2', 'm2'];

    $scope.eui_units = [
      'kBtu/ft2',
      'kBtu/m2',
      'kWh/ft2',
      'kWh/m2',
      'GJ/m2',
      'GJ/ft2'
    ];

    $scope.btnText = 'Expand Configurations';
    $scope.changeText = (btnText) => {
      if (btnText === 'Collapse Configurations') {
        $scope.btnText = 'Expand Configurations';
      } else {
        $scope.btnText = 'Collapse Configurations';
      }
    };

    /* save settings */
    $scope.save_settings = () => {
      $scope.settings_updated = false;
      if ($scope.conf.id) {
        // update
        statistics_service
          .update_statistic($scope.org.id, $scope.conf.id, $scope.conf)
          .then((response) => {
            if (response.status === 'error') {
              $scope.config_errors = response.errors;
            } else {
              statistics_service.get_statistics($scope.org.id).then((data) => {
                $scope.conf = data.length > 0 ? data[0] : {};
              });
              $scope.settings_updated = true;
            }
          })
          .catch((response) => {
            if (response.data && response.data.status === 'error') {
              $scope.config_errors = response.data.message;
            } else {
              $scope.config_errors = 'An unknown error has occurred';
            }
            Notification.error({ message: `Error: ${$scope.config_errors}`, delay: 15000, closeOnClick: true });
          });
      } else {
        // create
        statistics_service
          .new_statistic($scope.org.id, $scope.conf)
          .then(() => {
            statistics_service.get_statistics($scope.org.id).then((data) => {
              $scope.conf = data.length > 0 ? data[0] : {};
            });
            $scope.settings_updated = true;
          })
          .catch((response) => {
            if (response.data && response.data.status === 'error') {
              $scope.config_errors = response.data.message;
            } else {
              $scope.config_errors = 'An unknown error has occurred';
            }
            Notification.error({ message: `Error: ${$scope.config_errors}`, delay: 15000, closeOnClick: true });
          });
      }
    };

    /* calculate stats and update data display */
    $scope.calculate = () => {
      // calculate statistics
      statistics_service
        .calculate_statistics($scope.org.id, $scope.conf.id)
        .then((response) => {
          if (response.status === 'error') {
            $scope.config_errors = response.errors;
          } else {
            // fetched data
            $scope.data = response.data.data;
            // $scope.boxplotData = {};
            // $scope.elec_chart = $scope.create_chart('canvas_elec', $scope.data.chart_data_elec, 'Electricity Energy Use Intensity');
            // $scope.gas_chart = $scope.create_chart('canvas_gas', $scope.data.chart_data_gas, 'Natural Gas Energy Use Intensity');
            $scope.data_fetched = true;
          }
        })
        .catch((response) => {
          if (response.data && response.status === 'error') {
            $scope.config_errors = response.data.message;
          } else {
            $scope.config_errors = 'An unknown error has occurred';
          }
          Notification.error({ message: `Error: ${$scope.config_errors}`, delay: 15000, closeOnClick: true });
        });
    };

    // $scope.create_chart = (chartType, data, title_text) => {
    //   $scope.boxplotData[chartType] = {
    //     // define label tree
    //     // labels are the cycle in $scope.data
    //     labels: Object.keys(data),
    //     datasets: []
    //   };
    //   // iterate over keys of $scope.chart_data_elec hash and add data to datasets
    //   for (const key in data) {
    //     $scope.boxplotData[chartType].datasets.push({
    //       label: key,
    //       data: data[key]
    //     });
    //   }
    //   const canvas = document.getElementById(chartType);
    //   const ctx = canvas.getContext('2d');
    //   return new Chart(ctx, {
    //     type: 'boxplot',
    //     data: $scope.boxplotData[chartType],
    //     options: {
    //       responsive: true,
    //       legend: {
    //         position: 'top'
    //       },
    //       title: {
    //         display: true,
    //         text: title_text
    //       }
    //     }
    //   });
    // };
  }
]);
