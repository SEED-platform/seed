angular.module('BE.seed.controller.insights_property', [])
  .controller('insights_property_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'compliance_metrics',
    'compliance_metric_service',
    'organization_payload',
    'spinner_utility',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      compliance_metrics,
      compliance_metric_service,
      organization_payload,
      spinner_utility,
      cycles
    ) {

      $scope.id = $stateParams.id;
      $scope.cycles = cycles.cycles;
      $scope.static_url = urls.static_url;
      $scope.organization =  organization_payload.organization;

      // compliance metric
      $scope.compliance_metric = {};
      // for now there should always be 1 (get_or_create_default function in compliance_metrics list api)
      // in the future there will be multiple
      if (compliance_metrics.length > 0) {
        $scope.compliance_metric = compliance_metrics[0];
      }
      // console.log("COMPLIANCE METRIC: ", $scope.compliance_metric);

      // chart data
      $scope.data = null;
      $scope.chart_datasets = {};

      // default settings / dropdowns
      $scope.chart_cycle = _.last($scope.cycles).id;
      $scope.chart_cycle_name = _.last($scope.cycles).name;
      $scope.chart_metric = null;
      $scope.chart_xaxis = null;
      $scope.x_axis_options = [];
      $scope.y_axis_options = [];
      $scope.x_categorical = false;

      // load data
      let _load_data = function () {
        if (_.isEmpty($scope.compliance_metric)) {
          spinner_utility.hide();
          return;
        }
        spinner_utility.show();
        let data = compliance_metric_service.evaluate_compliance_metric($scope.compliance_metric.id).then((data) => {
          $scope.data = data;
          spinner_utility.hide();
        }).then(() => {
          console.log( "DATA RETURNED: ", $scope.data)
          if ($scope.data) {
            // set options
            // x axis
            $scope.x_axis_options = $scope.data.metric.x_axis_columns;

            if (_.size($scope.x_axis_options) > 0) {
              $scope.chart_xaxis = _.first($scope.x_axis_options).id;
            }
            // y axis
            if ($scope.data.metric.energy_metric == true){
              $scope.y_axis_options.push({'id': 0, 'name': 'Energy Metric'})
            }
            if ($scope.data.metric.emission_metric == true){
              $scope.y_axis_options.push({'id': 1, 'name': 'Emission Metric'})
            }
            if (_.size($scope.y_axis_options) > 0) {
              $scope.chart_metric = _.first($scope.y_axis_options).id;
            }

          }
          _rebuild_datasets();

          // once
          _build_chart();

        })
      };

      // display link with "org display field value" listed in table
      $scope.get_display_field_value = function(cycle_id, prop_id) {
        let name = null
        let record = _.find($scope.data.properties_by_cycles[cycle_id], {'property_view_id': prop_id})
        if (record) {
          name = _.find(record, function(v,k) {
            return _.startsWith(k, $scope.organization.property_display_field)
          });
        }

        return name ? name : prop_id
      }

      $scope.update = function() {
        spinner_utility.show();
        // console.log('chart_cycle is now: ', $scope.chart_cycle)
        // console.log('xaxis is now: ', $scope.chart_xaxis)
        // console.log('Metric is now: ', $scope.chart_metric)
        let record = _.find($scope.cycles, function(o) {
          return o.id == $scope.chart_cycle;
        });
        $scope.chart_cycle_name = record.name;

        // redraw dataset
        _rebuild_datasets();
        // update chart
        _update_chart();
        spinner_utility.hide();
      }

      const _rebuild_datasets = () => {
        console.log("REBUILD DATASETS")

        $scope.x_categorical = false;

        let datasets = [{'data': [], 'label': 'compliant', 'pointStyle': 'circle'},
        {'data': [], 'label': 'non-compliant', 'pointStyle': 'triangle', 'radius': 7},
        {'data': [], 'label': 'unknown', 'pointStyle': 'rect'}]

        let annotation =  {
          type: 'line',
          xMin: 0,
          xMax: 0,
          yMin: 0,
          yMax: 0,
          backgroundColor: '#333',
          borderWidth: 1,
          arrowHeads: {
            end: {
              display: true,
              width: 9,
              length: 0
            }
          }
        }

        $scope.annotations = {};

        _.forEach($scope.data.properties_by_cycles[$scope.chart_cycle], function(prop) {
          item = {'id': prop.property_view_id}
          item['name'] = _.find(prop, function(v,k) {
            return _.startsWith(k, 'property_name')
          });
          // x axis is easy
          item['x'] = _.find(prop, function(v, k) {
            return _.endsWith(k, '_' + String($scope.chart_xaxis));
          });

          // is x axis categorical?
          if ($scope.x_categorical == false && isNaN(item['x'])) {
            $scope.x_categorical = true;
          }

          // y axis depends on metric selection
          if ($scope.chart_metric == 0) {

            // ENERGY
            item['y'] = _.find(prop, function(v, k) {
              return _.endsWith(k, '_' + String($scope.data.metric.actual_energy_column));
            });
            if ($scope.data.metric.energy_bool == false) {
              item['target'] = _.find(prop, function(v, k) {
                return _.endsWith(k, '_' + String($scope.data.metric.target_energy_column));
              });
            }
          } else if ($scope.chart_metric == 1) {
            // EMISSIONS
            item['y'] = _.find(prop, function(v, k) {
              return _.endsWith(k, '_' + String($scope.data.metric.actual_emission_column));
            });
            if ($scope.data.metric.emission_bool == false) {
              item['target'] = _.find(prop, function(v, k) {
                return _.endsWith(k, '_' + String($scope.data.metric.target_emission_column));
              });
            }
          }

          // place in appropriate dataset
          if (_.includes($scope.data.results_by_cycles[$scope.chart_cycle]['y'], prop.property_view_id)) {
            // compliant dataset
            datasets[0]['data'].push(item);
          } else if (_.includes($scope.data.results_by_cycles[$scope.chart_cycle]['n'], prop.property_view_id)) {
            // non-compliant dataset
            datasets[1]['data'].push(item);

            // add whisker annotation
            // only when we are displaying the non-compliant metric (energy or emission)
            // don't add whisker if data is in range for that metric or it looks bad
            let add = false
            metric_type = $scope.chart_metric == 0 ? $scope.data.metric.energy_metric_type : $scope.data.metric.emission_metric_type;
            if (item['x'] && item['y'] && item['target']) {
              if ((metric_type == 1 && (item['target'] < item['y'])) || (metric_type == 2 && (item['target'] > item['y']))) {
                add = true
              }
            }

            if (add) {
              // add it
              let anno = Object.assign({},annotation)
              anno.xMin = item['x']
              anno.xMax = item['x']
              anno.yMin = item['y']
              anno.yMax = item['target']
              $scope.annotations['prop' + prop.property_view_id] = anno
            }

          } else {
            // unknown dataset
            datasets[2]['data'].push(item);
          }
        });

        console.log("DATASETS BUILT: ", datasets);
        $scope.chart_datasets = datasets;
        //console.log("ANNOTATIONS: ", $scope.annotations);
      }

      // CHARTS
      var colors = {'compliant': '#77CCCB', 'non-compliant': '#A94455', 'unknown': '#DDDDDD'}

      const tooltip_footer = (tooltipItems) => {
        let text = ''
        tooltipItems.forEach(function(tooltipItem) {
          text = 'ID: ' + tooltipItem.raw.id + '\n' + 'name: ' + tooltipItem.raw.name;
        });

        return text;
      };

      const _build_chart = () => {
        console.log('BUILD CHART')
        if (!$scope.chart_datasets) {
          console.log('NO DATA')
          return
        }
        const canvas = document.getElementById('property-insights-chart')
        const ctx = canvas.getContext('2d')


        $scope.insightsChart = new Chart(ctx, {
          type: 'scatter',
          data: {
          },
          options: {
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
                  footer: tooltip_footer,
                }
              },
              annotation: {
                annotations: {
                  box1: {
                    // Indicates the type of annotation
                    type: 'line',
                    xMin: 1990,
                    xMax: 1990,
                    yMin: 60,
                    yMax: 40,
                    backgroundColor: '#333',
                    arrowHeads: {
                      end: {
                        display: true,
                        width: 9,
                        length: 0
                      }
                    }
                  }
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
                  callback: function(value) {
                    return this.getLabelForValue(value)
                  }
                },
                type: 'linear'
              },
              y: {
                beginAtZero: true,
                stacked: true,
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

        // load data
        console.log('UPDATE CHART');
        _update_chart();
        console.log('BUILD CHART COMPLETE ')
        console.log("CHART DATA: ", $scope.insightsChart.data)

      }

      const _update_chart = () => {
        let x_index = _.findIndex($scope.data.metric.x_axis_columns, {'id': $scope.chart_xaxis});
        let x_axis_name = $scope.data.metric.x_axis_columns[x_index].display_name;

        let y_axis_name = null;
        if ($scope.chart_metric ==  0){
          y_axis_name = $scope.data.metric.actual_energy_column_name;
        } else if ($scope.chart_metric == 1){
          y_axis_name = $scope.data.metric.actual_emission_column_name;
        }

        // update axes
        $scope.insightsChart.options.scales.x.title.text = x_axis_name;
        $scope.insightsChart.options.scales.y.title.text = y_axis_name;

        // check if x-axis is categorical
        $scope.insightsChart.options.scales.x.type = $scope.x_categorical == true ? 'category' : 'linear'

        // update annotations
        $scope.insightsChart.options.plugins.annotation.annotations = $scope.annotations;

        // update chart datasets
        $scope.insightsChart.data.datasets = $scope.chart_datasets;
        _.forEach($scope.insightsChart.data.datasets, function(ds) {
          ds['backgroundColor'] = colors[ds['label']]
        });

        // update x axis ticks (for year)
        if (_.includes(_.lowerCase(x_axis_name), 'year')) {

          $scope.insightsChart.options.scales.x.ticks = { callback: function(value, index, ticks) {
            return this.getLabelForValue(value).replace(',', '')
          } }
        } else {
          $scope.insightsChart.options.scales.x.ticks = { callback: function(value) {
            return this.getLabelForValue(value)
          } }
        }

        // labels needed for categorical?
        $scope.insightsChart.data.labels = [];
        if ($scope.x_categorical) {
          let labels = [];
          _.forEach($scope.chart_datasets, function(ds) {
            labels = _.uniq(_.concat(labels, _.map(ds['data'], 'x')))
          });
          labels = labels.filter(function( element ) {
             return element !== undefined;
          });
          $scope.insightsChart.data.labels = labels;
        }

        console.log("REFRESH CHART");
        $scope.insightsChart.update()

      }

      _load_data();

    }

  ]);
