describe("controller: buildings_reports_controller", function(){
    // globals set up and used in each test scenario
    var mockService, scope, controller, ngFilter;
    var buildings_reports_ctrl, buildings_reports_ctrl_scope, labels;
    var mock_buildings_reports_service;
    var fake_report_data;
    var fake_aggregated_report_data;

    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function(
          $controller,
          $rootScope,
          $q,
          buildings_reports_service,
          $filter) {
            controller = $controller;
            scope = $rootScope;
            building_detail_ctrl_scope = $rootScope.$new();

            // mock the buildings_reports_service factory methods used in the controller
            // and return their promises
            mock_buildings_reports_service = buildings_reports_service;

            spyOn(mock_buildings_reports_service, "get_report_data")
                .andCallFake(function (building, org_id){
                    mock_building = building;
                     /* Assume test will ask for site_eui vs. gross_floor_area */
                    return $q.when(
                        fake_report_data
                    );
                }
            );

            spyOn(mock_buildings_reports_service, "get_aggregated_building_report_data")
                .andCallFake(function (building, org_id){
                    mock_building = building;
                     /* Assume test will ask for site_eui vs. gross_floor_area */
                    return $q.when(
                        fake_aggregated_report_data
                    );
                }
            );


        }
    ));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_building_detail_controller(){

        var fake_report_data = {
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
                    id: 5321
                    x: 70
                    y: 20000
                    yr_e: "2011-12-31"   
                },
                {
                    id: 5322
                    x: 71
                    y: 40000
                    yr_e: "2011-12-31"   
                },
                {
                    id: 5321
                    x: 73.1
                    y: 20000
                    yr_e: "2012-12-31"   
                },
                {
                    id: 5322
                    x: 75
                    y: 40000
                    yr_e: "2012-12-31"   
                },
            ],
            "num_buildings": 25,
            "num_buildings_w_data": 23
                       
        }

        var fake_aggregated_report_data = {
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
                    x: 70
                    y: '100-199k'
                    yr_e: "2011-12-31"   
                },
                {
                    x: 71
                    y: '200-299k'
                    yr_e: "2011-12-31"   
                },
                {
                    x: 73.1
                    y: '100-199k'
                    yr_e: "2012-12-31"   
                },
                {
                    x: 75
                    y: '200-299k'
                    yr_e: "2012-12-31"   
                },
            ],
            "num_buildings": 25,
            "num_buildings_w_data": 23
        }
        
        buildings_reports_ctrl = controller('buildings_reports_controller', {
            $scope: buildings_reports_ctrl_scope,

        });
    }

    /*
     * Test scenarios
     */

    it("should create the initial charts based on defaults", function() {
        //to do
    });

});
