describe("controller: buildings_reports_controller", function(){
    // globals set up and used in each test scenario
    var scope, controller;
    var buildings_reports_ctrl, buildings_reports_ctrl_scope, labels;
    var mock_buildings_reports_service;
    var fake_report_data_payload;
    var fake_aggregated_report_data_payload;
    var log;

    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function(
          $controller,
          $rootScope,
          $q,
          $log,
          buildings_reports_service) {
            controller = $controller;
            scope = $rootScope;
            log = $log;
            buildings_reports_ctrl_scope = $rootScope.$new();

            // mock the buildings_reports_service factory methods used in the controller
            // and return their promises
            mock_buildings_reports_service = buildings_reports_service;

            spyOn(mock_buildings_reports_service, "get_report_data")
                .andCallFake(function (xVar, yVar, startDate, endDate){
                    return $q.when(fake_report_data_payload);
                }
            );

            spyOn(mock_buildings_reports_service, "get_aggregated_report_data")
                .andCallFake(function (xVar, yVar, startDate, endDate){
                    return $q.when(fake_aggregated_report_data_payload);
                }
            );


        }
    ));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_buildings_reports_controller(){

        /* Assuming site_eui vs. gross_floor_area */
        fake_report_data_payload = {
            "status": "success",
            "building_counts" : [
                {   "yr_e": "Dec 31,2011",
                    "num_buildings": 10, 
                    "num_buildings_w_data": 9
                },
                {
                    "yr_e": "Dec 31,2012",
                    "num_buildings": 15,
                    "num_buildings_w_data": 14
                }
            ],
            "report_data": [
                {
                    id: 5321,
                    x: 70,
                    y: 20000,
                    yr_e: "2011-12-31"   
                },
                {
                    id: 5322,
                    x: 71,
                    y: 40000,
                    yr_e: "2011-12-31"   
                },
                {
                    id: 5321,
                    x: 73.1,
                    y: 20000,
                    yr_e: "2012-12-31"   
                },
                {
                    id: 5322,
                    x: 75,
                    y: 40000,
                    yr_e: "2012-12-31"   
                },
            ]                       
        }

        /* Assuming site_eui vs. gross_floor_area */
        fake_aggregated_report_data_payload = {
            "status": "success",
            "building_counts" : [
                {   "yr_e": "Dec 31,2011",
                    "num_buildings": 10, 
                    "num_buildings_w_data": 9
                },
                {
                    "yr_e": "Dec 31,2012",
                    "num_buildings": 15,
                    "num_buildings_w_data": 14
                }
            ],
            "report_data": [
                {
                    x: 70,
                    y: '100-199k',
                    yr_e: "2011-12-31" ,  
                },
                {
                    x: 71,
                    y: '200-299k',
                    yr_e: "2011-12-31"   
                },
                {
                    x: 73.1,
                    y: '100-199k',
                    yr_e: "2012-12-31"   
                },
                {
                    x: 75,
                    y: '200-299k',
                    yr_e: "2012-12-31"   
                },
            ]
        }
        
        buildings_reports_ctrl = controller('buildings_reports_controller', {
            $scope: buildings_reports_ctrl_scope,
            $log: log,
            buildings_reports_service: mock_buildings_reports_service
        });
    }

    /*
     * Test scenarios
     */
    it("should have proper settings for the range of x and y variables", function() {
        
        // arrange
        create_buildings_reports_controller();
        
        // no action, go straight to assertions to check defaults

        // assertions
        var numXVars = buildings_reports_ctrl_scope.xAxisVars.length;
        for (var xIndex=0;xIndex<numXVars;xIndex++){
            var xVarDef = buildings_reports_ctrl_scope.xAxisVars[xIndex];
            expect(xVarDef.name).toBeDefined();
            expect(xVarDef.label).toBeDefined();
            expect(xVarDef.axisLabel).toBeDefined();
            expect(xVarDef.axisType).toBeDefined();
            expect(xVarDef.axisTickFormat).toBeDefined();
        }
        var numYVars = buildings_reports_ctrl_scope.yAxisVars.length;
        for (var yIndex=0;yIndex<numYVars;yIndex++){
            var yVarDef = buildings_reports_ctrl_scope.yAxisVars[yIndex];
            expect(yVarDef.name).toBeDefined();
            expect(yVarDef.label).toBeDefined();
            expect(yVarDef.axisLabel).toBeDefined();
            expect(yVarDef.axisType).toBeDefined();
            expect(yVarDef.axisTickFormat).toBeDefined();
        }
    });   
    it("should have defaults for selected x and y variable", function(){
        // arrange
        create_buildings_reports_controller();
        
        // no action, go straight to assertions to check defaults

        // assertions
        expect(buildings_reports_ctrl_scope.xAxisSelectedItem).toBeDefined();
        expect(buildings_reports_ctrl_scope.yAxisSelectedItem).toBeDefined();          
    }); 
    it("should load data from service and assign it to scope variables and build the chart configuration objects", function() {
        // arrange
        create_buildings_reports_controller();

        // act
        buildings_reports_ctrl_scope.$digest();
        buildings_reports_ctrl_scope.updateChartData();
        buildings_reports_ctrl_scope.$digest();

        // assertions
        //make sure data from (mock) service is loaded correctly
        expect(buildings_reports_ctrl_scope.chartData.chartData).toEqual(fake_report_data_payload.chartData);
        expect(buildings_reports_ctrl_scope.aggChartData.chartData).toEqual(fake_aggregated_report_data_payload.chartData);
    
        //make sure titles are set
        expect(buildings_reports_ctrl_scope.chart1Title).toBeDefined();
        expect(buildings_reports_ctrl_scope.chart2Title).toBeDefined();

        //make sure colors are set right, based on the incoming (mock) building_counts.
        var bldgCounts = fake_report_data_payload.building_counts
        var bldgCountsAgg = fake_aggregated_report_data_payload.building_counts
        var defaultColors = buildings_reports_ctrl_scope.defaultColors;
        var chartData = buildings_reports_ctrl_scope.chartData;
        var aggChartData = buildings_reports_ctrl_scope.aggChartData;

        expect(chartData.colors.length).toEqual(bldgCounts.length);
        expect(chartData.colors[0].seriesName).toEqual(bldgCounts[0].yr_e);
        expect(chartData.colors[0].color).toEqual(defaultColors[0]);
        expect(chartData.colors[1].seriesName).toEqual(bldgCounts[1].yr_e);
        expect(chartData.colors[1].color).toEqual(defaultColors[1]);

        expect(aggChartData.colors.length).toEqual(bldgCountsAgg.length);
        expect(aggChartData.colors[0].seriesName).toEqual(bldgCountsAgg[0].yr_e);
        expect(aggChartData.colors[0].color).toEqual(defaultColors[0]);
        expect(aggChartData.colors[1].seriesName).toEqual(bldgCountsAgg[1].yr_e);
        expect(aggChartData.colors[1].color).toEqual(defaultColors[1]);
    });
    


});
