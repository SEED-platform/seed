/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.insights_property', []).controller('insights_property_controller', [
  '$scope',
  '$state',
  '$stateParams',
  '$uibModal',
  'urls',
  'compliance_metrics',
  'compliance_metric_service',
  'organization_payload',
  'spinner_utility',
  'auth_payload',
  // eslint-disable-next-line func-names
  function ($scope, $state, $stateParams, $uibModal, urls, compliance_metrics, compliance_metric_service, organization_payload, spinner_utility, auth_payload) {
    $scope.id = $stateParams.id;
    $scope.static_url = urls.static_url;
    $scope.organization = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    // toggle help
    $scope.show_help = false;
    $scope.toggle_help = () => {
      $scope.show_help = !$scope.show_help;
    }

    // configs ($scope.configs set to saved_configs where still applies.
    // for example, if saved_configs.compliance_metric is 1, but 1 has been deleted, it does apply.)
    const saved_configs = JSON.parse(localStorage.getItem(`insights.property.configs.${$scope.organization.id}`));
    $scope.configs = {
      compliance_metric: {},
      chart_cycle: null,
      chart_metric: null,
      chart_xaxis: null,
      dataset_visibility: saved_configs?.dataset_visibility ?? [true, true, true],
      annotation_visibility: saved_configs?.annotation_visibility ?? true
    };

    // compliance metric
    $scope.compliance_metrics = compliance_metrics;
    $scope.selected_metric = null;
    $scope.initialize_chart = true;

    const set_init_compliance_metric = (saved_configs) => {
      // try saved_compliance_metric
      if (saved_configs?.compliance_metric_id) {
        const saved_compliance_metric = compliance_metrics.find((cm) => cm.id === saved_configs.compliance_metric_id);
        if (saved_compliance_metric) {
          $scope.configs.compliance_metric = saved_compliance_metric;
          $scope.selected_metric = $scope.configs.compliance_metric.id;
          return;
        }
      }

      // else use first compliance_metric
      if (compliance_metrics.length > 0) {
        $scope.configs.compliance_metric = compliance_metrics[0];
        $scope.selected_metric = $scope.configs.compliance_metric.id;
      }
    };
    set_init_compliance_metric(saved_configs);

    // chart data
    $scope.data = null;
    $scope.chart_datasets = {};

    // default settings / dropdowns
    $scope.chart_cycle_name = null;
    $scope.cycles = [];
    $scope.x_axis_options = [];
    $scope.y_axis_options = [];
    $scope.x_categorical = false;

    $scope.$watch(
      'configs',
      (new_configs) => {
        const local_storage_configs = {
          ..._.omit(new_configs, 'compliance_metric'),
          compliance_metric_id: new_configs.compliance_metric.id
        };
        localStorage.setItem(`insights.property.configs.${$scope.organization.id}`, JSON.stringify(local_storage_configs));
      },
      true
    );

    // load data
    const _load_data = () => {
      if (_.isEmpty($scope.configs.compliance_metric)) {
        spinner_utility.hide();
        return;
      }
      spinner_utility.show();
      compliance_metric_service
        .evaluate_compliance_metric($scope.configs.compliance_metric.id)
        .then((data) => {
          $scope.data = data;
        })
        .then(() => {
          if ($scope.data) {
            // set options
            // cycles
            $scope.cycles = $scope.data.metric.cycles;
            if (_.size($scope.cycles) > 0) {
              // used saved cycle
              if (saved_configs?.chart_cycle) {
                const saved_cycle = $scope.cycles.find((c) => c.id === saved_configs.chart_cycle);
                if (saved_cycle !== undefined) {
                  $scope.configs.chart_cycle = saved_cycle.id;
                  $scope.chart_cycle_name = saved_cycle.name;
                }
                delete saved_configs.chart_cycle; // don't trigger this if again, only the first time.
              }

              // don't clear out a valid existing selection
              if (!$scope.configs.chart_cycle || !$scope.cycles.find(({ id }) => id === $scope.configs.chart_cycle)) {
                $scope.configs.chart_cycle = _.first($scope.cycles).id;
                $scope.chart_cycle_name = _.first($scope.cycles).name;
              }
            }

            // x axis

            $scope.x_axis_options = [...$scope.data.metric.x_axis_columns, { display_name: 'Ranked Distance to Compliance', id: 'Ranked' }];
            if (_.size($scope.x_axis_options) > 0) {
              // used saved chart_xaxis
              if (saved_configs?.chart_xaxis) {
                const saved_chart_xaxis = $scope.x_axis_options.find((c) => c.id === saved_configs.chart_xaxis);
                if (saved_chart_xaxis !== undefined) {
                  $scope.configs.chart_xaxis = saved_chart_xaxis.id;
                }
                delete saved_configs.chart_xaxis; // don't trigger this if again, only the first time.
              }

              // don't clear out a valid existing selection
              if (!$scope.configs.chart_xaxis || !$scope.x_axis_options.find(({ id }) => id === $scope.configs.chart_xaxis)) {
                $scope.configs.chart_xaxis = _.first($scope.x_axis_options).id;
              }
            }
            // y axis
            $scope.y_axis_options = [];
            if ($scope.data.metric.energy_metric === true) {
              $scope.y_axis_options.push({ id: 0, name: 'Energy Metric' });
            }
            if ($scope.data.metric.emission_metric === true) {
              $scope.y_axis_options.push({ id: 1, name: 'Emission Metric' });
            }
            if (_.size($scope.y_axis_options) > 0) {
              // used saved chart_metric
              if (saved_configs?.chart_metric) {
                const saved_chart_metric = $scope.y_axis_options.find((c) => c.id === saved_configs.chart_metric);
                if (saved_chart_metric !== undefined) {
                  $scope.configs.chart_metric = saved_chart_metric.id;
                }
                delete saved_configs.saved_chart_metric; // don't trigger this if again, only the first time.
              }

              // don't clear out a valid existing selection
              if (!$scope.configs.chart_metric || !$scope.y_axis_options.find(({ id }) => id === $scope.configs.chart_metric)) {
                $scope.configs.chart_metric = _.first($scope.y_axis_options).id;
              }
            }
          }
          _rebuild_datasets();

          // once
          _build_chart();
        })
        .finally(() => {
          spinner_utility.hide();
        });
    };

    $scope.update = () => {
      spinner_utility.show();

      const record = _.find($scope.cycles, (o) => o.id === $scope.configs.chart_cycle);
      $scope.chart_cycle_name = record.name;

      // redraw dataset
      _rebuild_datasets();
      // update chart
      _update_chart();
      spinner_utility.hide();
    };

    $scope.update_metric = () => {
      spinner_utility.show();

      // compliance metric
      $scope.configs.compliance_metric = _.find($scope.compliance_metrics, (o) => o.id === $scope.selected_metric);

      // reload data for selected metric
      _load_data();

      // redraw dataset
      _rebuild_datasets();
      // update chart
      _update_chart();
      spinner_utility.hide();
    };

    const _rebuild_datasets = () => {
      $scope.x_categorical = false;

      const datasets = [
        { data: [], label: 'compliant', pointStyle: 'circle' },
        {
          data: [], label: 'non-compliant', pointStyle: 'triangle', radius: 7
        },
        { data: [], label: 'unknown', pointStyle: 'rect' }
      ];

      $scope.display_annotation = true;
      const annotation = {
        type: 'line',
        xMin: 0,
        xMax: 0,
        yMin: 0,
        yMax: 0,
        backgroundColor: '#333',
        borderWidth: 1,
        display: (ctx) => $scope.display_annotation,
        arrowHeads: {
          end: {
            display: true,
            width: 9,
            length: 0
          }
        }
      };

      $scope.annotations = {};

      _.forEach($scope.data.properties_by_cycles[$scope.configs.chart_cycle], (prop) => {
        const item = { id: prop.property_view_id };
        item.name = _.find(prop, (v, k) => k.startsWith($scope.organization.property_display_field));
        // x axis is easy
        item.x = _.find(prop, (v, k) => k.endsWith(`_${String($scope.configs.chart_xaxis)}`));

        // is x axis categorical?
        if ($scope.x_categorical === false && Number.isNaN(item.x)) {
          $scope.x_categorical = true;
        }

        // y axis depends on metric selection
        if ($scope.configs.chart_metric === 0) {
          // ENERGY
          item.y = _.find(prop, (v, k) => k.endsWith(`_${String($scope.data.metric.actual_energy_column)}`));
          if ($scope.data.metric.energy_bool === false) {
            item.target = _.find(prop, (v, k) => k.endsWith(`_${String($scope.data.metric.target_energy_column)}`));
          }
        } else if ($scope.configs.chart_metric === 1) {
          // EMISSIONS
          item.y = _.find(prop, (v, k) => k.endsWith(`_${String($scope.data.metric.actual_emission_column)}`));
          if ($scope.data.metric.emission_bool === false) {
            item.target = _.find(prop, (v, k) => k.endsWith(`_${String($scope.data.metric.target_emission_column)}`));
          }
        }

        // place in appropriate dataset
        if (_.includes($scope.data.results_by_cycles[$scope.configs.chart_cycle].y, prop.property_view_id)) {
          // compliant dataset
          datasets[0].data.push(item);
        } else if (_.includes($scope.data.results_by_cycles[$scope.configs.chart_cycle].n, prop.property_view_id)) {
          // non-compliant dataset
          datasets[1].data.push(item);
        } else {
          // unknown dataset
          datasets[2].data.push(item);
        }
      });
      const non_compliant = datasets.find((ds) => ds.label === 'non-compliant');

      // Rank
      if ($scope.configs.chart_xaxis === 'Ranked') {
        non_compliant.data.sort((a, b) => {
          const a_diff = Math.abs(a.y - a.target);
          const b_diff = Math.abs(b.y - b.target);

          return b_diff - a_diff;
        });
        non_compliant.data.forEach((d, i) => {
          d.x = i;
        });
      }

      // add whisker annotation
      non_compliant.data.forEach((item) => {
        // only when we are displaying the non-compliant metric (energy or emission)
        // don't add whisker if data is in range for that metric or it looks bad
        item.distance = null;
        let add = false;
        const metric_type = $scope.configs.chart_metric === 0 ? $scope.data.metric.energy_metric_type : $scope.data.metric.emission_metric_type;
        if (item.x && item.y && item.target) {
          if ((metric_type === 1 && item.target < item.y) || (metric_type === 2 && item.target > item.y)) {
            add = true;
            item.distance = Math.abs(item.target - item.y)
          }
        }

        if (add) {
          // add it
          const anno = { ...annotation };
          anno.xMin = item.x;
          anno.xMax = item.x;
          anno.yMin = item.y;
          anno.yMax = item.target;
          $scope.annotations[`prop${item.id}`] = anno;
        }
      });

      $scope.chart_datasets = datasets;
    };

    // CHARTS
    const colors = { compliant: '#77CCCB', 'non-compliant': '#A94455', unknown: '#DDDDDD' };

    const _build_chart = () => {
      if (!$scope.chart_datasets) {
        return;
      }

      // do this once
      if ($scope.initialize_chart) {
        const canvas = document.getElementById('property-insights-chart');
        const ctx = canvas.getContext('2d');

        $scope.insightsChart = new Chart(ctx, {
          type: 'scatter',
          data: {},
          options: {
            onClick: (event) => {
              const activePoints = event.chart.getActiveElements(event);

              if (activePoints[0]) {
                const activePoint = activePoints[0];
                const item = event.chart.data.datasets[activePoint.datasetIndex].data[activePoint.index];
                $state.go('inventory_detail', { inventory_type: 'properties', view_id: item.id });
              }
            },
            elements: {
              point: {
                radius: 5
              }
            },
            plugins: {
              title: {
                display: true,
                align: 'start'
              },
              legend: {
                display: false
              },
              tooltip: {
                callbacks: {
                  label: function(context) {
                    let text = [];
                    // property ID / default display field
                    if (context.raw.name) {
                      text.push(`Property: ${context.raw.name}`);
                    } else {
                      text.push(`Property ID: ${context.raw.id}`);
                    }

                    // x and y axis names and values
                    const x_index = _.findIndex($scope.x_axis_options, { id: $scope.configs.chart_xaxis });
                    const x_axis_name = $scope.x_axis_options[x_index]?.display_name;
                    let y_axis_name = null;
                    if ($scope.configs.chart_metric === 0) {
                      y_axis_name = $scope.data.metric.actual_energy_column_name;
                    } else if ($scope.configs.chart_metric === 1) {
                      y_axis_name = $scope.data.metric.actual_emission_column_name;
                    }

                    text.push(`${x_axis_name}: ${context.parsed.x}`);
                    text.push(`${y_axis_name}: ${context.parsed.y}`);
                    return text;
                  }
                }
              },
              zoom: {
                limits: {
                  x: { min: 'original', max: 'original', minRange: 50 },
                  y: { min: 'original', max: 'original', minRange: 50 }
                },
                pan: {
                  enabled: true,
                  mode: 'xy'
                },
                zoom: {
                  wheel: {
                    enabled: true
                  },
                  mode: 'xy'
                }
              },
              annotation: {
                annotations: {
                  // box1: {
                  //   // Indicates the type of annotation
                  //   type: 'line',
                  //   xMin: 1990,
                  //   xMax: 1990,
                  //   yMin: 60,
                  //   yMax: 40,
                  //   backgroundColor: '#333',
                  //   arrowHeads: {
                  //     end: {
                  //       display: true,
                  //       width: 9,
                  //       length: 0
                  //     }
                  //   }
                  // }
                }
              }
            },
            scales: {
              x: {
                title: {
                  text: 'X',
                  display: true
                },
                ticks: {
                  callback(value) {
                    return this.getLabelForValue(value);
                  }
                },
                type: 'linear'
              },
              y: {
                beginAtZero: true,
                position: 'left',
                display: true,
                title: {
                  text: 'Y',
                  display: true
                }
              }
            }
          }
        });
        $scope.initialize_chart = false;
      }

      // load data
      _update_chart();
    };

    $scope.downloadChart = () => {
      const a = document.createElement('a');
      a.href = $scope.insightsChart.toBase64Image();
      a.download = 'Property Insights.png';
      a.click();
    };

    const _update_chart = () => {
      const x_index = _.findIndex($scope.x_axis_options, { id: $scope.configs.chart_xaxis });
      const x_axis_name = $scope.x_axis_options[x_index]?.display_name;

      let y_axis_name = null;
      if ($scope.configs.chart_metric === 0) {
        y_axis_name = $scope.data.metric.actual_energy_column_name;
      } else if ($scope.configs.chart_metric === 1) {
        y_axis_name = $scope.data.metric.actual_emission_column_name;
      }

      // update axes
      $scope.insightsChart.options.scales.x.title.text = x_axis_name;
      $scope.insightsChart.options.scales.y.title.text = y_axis_name;

      // check if x-axis is categorical
      $scope.insightsChart.options.scales.x.type = $scope.x_categorical === true ? 'category' : 'linear';

      // update annotations
      $scope.insightsChart.options.plugins.annotation.annotations = $scope.annotations;

      // update chart datasets
      $scope.insightsChart.data.datasets = $scope.chart_datasets;
      _.forEach($scope.insightsChart.data.datasets, (ds) => {
        ds.backgroundColor = colors[ds.label];
      });

      // update x axis ticks (for year)
      if (x_axis_name && x_axis_name.toLowerCase().includes('year')) {
        $scope.insightsChart.options.scales.x.ticks = {
          callback(value) {
            return this.getLabelForValue(value).replace(',', '');
          }
        };
      } else {
        $scope.insightsChart.options.scales.x.ticks = {
          callback(value) {
            return this.getLabelForValue(value);
          }
        };
      }

      // labels needed for categorical?
      $scope.insightsChart.data.labels = [];
      if ($scope.x_categorical) {
        let labels = [];
        _.forEach($scope.chart_datasets, (ds) => {
          labels = _.uniq(_.concat(labels, _.map(ds.data, 'x')));
        });
        labels = labels.filter((element) => element !== undefined);
        $scope.insightsChart.data.labels = labels;
      }

      // set visibility
      $scope.configs.dataset_visibility.forEach((is_visible, index) => {
        $scope.insightsChart.setDatasetVisibility(index, is_visible);
      });
      $scope.display_annotation = saved_configs?.annotation_visibility ?? true;

      $scope.insightsChart.update();
    };

    $scope.toggle_dataset_visibility = (index) => {
      const is_visible = $scope.insightsChart.isDatasetVisible(index);
      $scope.insightsChart.setDatasetVisibility(index, !is_visible);
      $scope.insightsChart.update();

      $scope.configs.dataset_visibility[index] = !is_visible;
    };

    $scope.toggle_annotation_visibility = () => {
      $scope.display_annotation = !$scope.display_annotation;
      $scope.insightsChart.update();

      $scope.configs.annotation_visibility = $scope.display_annotation;
    };

    setTimeout(_load_data, 0); // avoid race condition with route transition spinner.

    $scope.visibleIds = () => {
      const visibleDatasets = $scope.insightsChart?.data.datasets.filter((d, i) => $scope.insightsChart.isDatasetVisible(i)) ?? [];
      return visibleDatasets.reduce((acc, dataset) => [...acc, ...dataset.data.map(({ id }) => id)], []);
    };

    $scope.open_update_labels_modal = () => {
      $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/update_item_labels_modal.html`,
        controller: 'update_item_labels_modal_controller',
        resolve: {
          inventory_ids: $scope.visibleIds,
          inventory_type: () => 'properties'
        }
      });
    };
  }
]);
