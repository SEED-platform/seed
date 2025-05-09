/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('sdBasicPropertyInfoChart', []).directive('sdBasicPropertyInfoChart', [
  '$window',
  '$translate',
  ($window, $translate) => ({
    restrict: 'E',
    replace: true,
    scope: {
      onchartrendered: '&',
      data: '=',
      chartType: '@',
      height: '@'
    },
    require: ['sdBasicPropertyInfoChart'],
    link: (scope, element, attrs, controllers) => {
      const graphController = controllers[0];

      // init the chart
      graphController.setChartType(scope.chartType);
      graphController.createChartSVG();
      graphController.createChart();

      /**
         The 'data' object should have the following properties.

         series :          A string value indicating what the series for the dimple chart will be
         chartData :       An array of objects to serve as actual chart data
         xAxisTitle :      A string value for the x axis title
         yAxisTitle :      A string value for the y axis title
         yAxisType:        A string value indicating the type of axis (Dimple value, e.g., 'Measure')
         yAxisMin:         An integer value for the minimum value on the y axis
         xAxisTickFormat:  A string value for the y axis tick format  (Dimple value)
         yAxisTickFormat:  A string value for the y axis tick format  (Dimple value)
         colors :          An array of objects that defines the colors for the series.
         Each object with the following properties:
         "seriesName"  : A string value for the series name
         "color"       : A hexadecimal string for the color for this series

         */
      scope.$watch('data', (newValue) => {
        // If the new value is empty or has properties but 'chartData' is empty, just clear the chart and return
        if (_.isEmpty(_.get(newValue, 'chartData'))) {
          graphController.clearChart();
          return;
        }

        if (_.get(newValue, 'chartData')) {
          graphController.setYAxisType(newValue.yAxisType);
          graphController.updateChart(
            newValue.series,
            newValue.chartData,
            newValue.xAxisTitle,
            newValue.yAxisTitle,
            newValue.yAxisType,
            newValue.yAxisMin,
            newValue.xAxisTickFormat,
            newValue.yAxisTickFormat,
            newValue.colors
          );
          scope.onchartrendered();
        }
      });

      angular.element($window).bind('resize', () => {
        graphController.resizeChart();
      });
    },
    controller: [
      '$scope',
      '$element',
      // eslint-disable-next-line func-names
      function ($scope, $element) {
        let id;
        let svg;
        let chart;
        let xAxis;
        let yAxis;
        let yAxisType = 'Measure';
        let hasData = false;
        let chartType = '';
        const self = this;
        const truncateLength = 15;

        // eslint-disable-next-line new-cap
        const defaultColors = [new dimple.color('#458cc8'), new dimple.color('#c83737'), new dimple.color('#1159a3'), new dimple.color('#f2c41d'), new dimple.color('#939495')];

        const width = '100%';
        const { height } = $scope;

        /* Create the <div> that holds the svg and the svg itself.
           This method should only be called once. */
        this.createChartSVG = () => {
          id = (Math.random() * 1e9).toString(36).replace('.', '_');
          $element.append(`<div class='dimple-graph' id='dng-${id}'></div>`);

          // create an svg element
          const svgID = `#dng-${id}`;
          svg = dimple.newSvg(svgID, width, height);
        };

        /*  Define the Dimple chart and load data based on the configuration and data arguments passed in.
           We do a complete recreation of the chart each time this method is called.  */
        this.updateChart = (series, chartData, xAxisTitle, yAxisTitle, yAxisType, yAxisMin, xAxisTickFormat, yAxisTickFormat, colors) => {
          self.clearChart();
          self.createChart();
          self.createChartAxes(yAxisType, yAxisMin, xAxisTickFormat, yAxisTickFormat);

          // setup colors
          if (colors && colors.length > 0) {
            const numColors = colors.length;
            for (let index = 0; index < numColors; index++) {
              const obj = colors[index];
              chart.assignColor(obj.seriesName, obj.color, obj.color, 1);
            }
          } else {
            chart.defaultColors = defaultColors;
          }

          // set type of chart and the series it will use to group data
          let s;
          if (chartType === 'bar') {
            s = chart.addSeries(series, dimple.plot.bar);
          } else {
            s = chart.addSeries(series, dimple.plot.bubble);
          }
          s.getTooltipText = (e) => {
            const arr = [];
            arr.push(`${$translate.instant('Year Ending')} : ${e.aggField[1]}`);
            arr.push(`${yAxisTitle} : ${e.cy.toString()}`);
            arr.push(`${xAxisTitle} : ${e.cx.toString()}`);
            return arr;
          };

          // attach data and titles and redraw
          chart.data = chartData;
          hasData = chart.data && chart.data.length > 0;
          xAxis.title = xAxisTitle;
          yAxis.title = yAxisTitle;
          if (yAxisMin) {
            yAxis.overrideMin = yAxisMin;
          }

          chart.draw(0);
        };

        /*  Create the Dimple chart, attaching it to pre-existing svg element.
           This method can be called each time we need a complete refresh.  */
        this.createChart = () => {
          // create the dimple chart using the d3 selection of our <svg> element
          // eslint-disable-next-line new-cap
          chart = new dimple.chart(svg, []);
          chart.defaultColors = defaultColors;
          chart.setMargins(120, 20, 60, 40);

          chart.noFormats = false; // use autostyle
          chart.draw(0);
        };

        const my_custom_format = (value) => {
          if (value && value.length > truncateLength) {
            return `${value.substring(0, truncateLength)}...`;
          }
          return value;
        };

        /* Create the axes for the chart, using value passed in from external controller. */
        this.createChartAxes = (yAxisType, yAxisMin, xAxisTickFormat, yAxisTickFormat) => {
          if (!xAxisTickFormat) {
            xAxisTickFormat = ',.0f';
          }

          xAxis = chart.addMeasureAxis('x', 'x');
          xAxis.tickFormat = xAxisTickFormat;

          if (yAxisType === 'Measure') {
            if (!yAxisTickFormat) {
              yAxisTickFormat = ',.0f';
            }
            yAxis = chart.addMeasureAxis('y', 'y');
            yAxis.tickFormat = yAxisTickFormat;
          } else {
            yAxis = chart.addCategoryAxis('y', ['y', 'yr_e']);
            yAxis.addOrderRule('y', false);
            yAxis._getFormat = () => my_custom_format;
          }
        };

        this.createChartLegend = () => {
          chart.addLegend(200, 10, 360, 20, 'right bottom');
        };

        this.clearChart = () => {
          if (_.get(chart, 'svg') && hasData) {
            chart.svg.selectAll('*').remove();
            hasData = false;
          }
        };

        this.setChartType = (chType) => {
          chartType = chType;
        };

        this.resizeChart = () => {
          if (chart) {
            chart.draw(0, true);
          }
        };

        this.getYAxisType = () => yAxisType;

        this.setYAxisType = (value) => {
          yAxisType = value;
        };

        this.getChart = () => chart;

        this.draw = () => {
          chart.draw();
        };

        this.getID = () => id;
      }
    ]
  })
]);
