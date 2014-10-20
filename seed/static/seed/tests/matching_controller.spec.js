/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe("controller: matching_controller", function(){
    // globals set up and used in each test scenario
    var mock_buildging_services, scope, controller, delete_called;
    var matching_ctrl, matching_ctrl_scope, modalInstance, labels;


    // make the seed app available for each test
    // 'BE.seed' is created in TestFilters.html
    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function($controller, $rootScope, $modal, urls, $q, building_services) {
            controller = $controller;
            scope = $rootScope;
            matching_ctrl_scope = $rootScope.$new();

            mock_buildging_services = building_services;
            spyOn(mock_buildging_services, "get_PM_filter_by_counts")
                .andCallFake(function(import_file){
                    return $q.when(
                        {
                            "status": "success",
                            "unmatched": 5,
                            "matched": 10
                        }
                    );
                }
            );
            spyOn(mock_buildging_services, "save_match")
                .andCallFake(function(b1, b2, create){
                    return $q.when(
                        {
                            "status": "success",
                            "child_id": 3
                        }
                    );
                }
            );
        }
    ));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_dataset_detail_controller(){
        var buildings_payload = {
            buildings: [
                {
                    pm_property_id: 1,
                    tax_lot_id: null,
                    custom_id_1: 2,
                    gross_floor_area: 111,
                    matched: true,
                    id: 1,
                    children: [3],
                    coparent: {
                        pm_property_id: null,
                        tax_lot_id: 2,
                        custom_id_1: null,
                        gross_floor_area: 111,
                        id: 2,
                        children: [3]
                    }
                }
            ],
            number_matching_search: 1,
            number_returned: 1,
        };
        matching_ctrl = controller('matching_controller', {
            $scope: matching_ctrl_scope,
            buildings_payload: buildings_payload,
            all_columns: {
                fields: [{sort_column: 'pm_property_id'}]
            },
            default_columns: {
                columns: ['pm_property_id']
            },
            import_file_payload: {
                import_file: {
                    id: 1,
                    dataset: {
                        importfiles: [
                            {
                                id: 1,
                                name: "file_1.csv"
                            },
                            {
                                id: 2,
                                name: "file_2.csv"
                            }
                        ]
                    }
                }
            }
        });
    }

    /*
     * Test scenarios
     */

    it("should have a buildings payload with potential matches", function() {
        // arrange
        create_dataset_detail_controller();

        // act
        matching_ctrl_scope.$digest();
        var b = matching_ctrl_scope.buildings[0];

        // assertions
        expect(matching_ctrl_scope.buildings.length).toBe(1);
        expect(b.coparent.children).toEqual(b.children);
    });

    it("should show the number matched or unmatched", function() {
        // arrange
        create_dataset_detail_controller();

        // act
        matching_ctrl_scope.$digest();

        // assertions
        expect(matching_ctrl_scope.matched_buildings).toEqual(10);
        expect(matching_ctrl_scope.unmatched_buildings).toEqual(5);
    });

    it("should jump back to the matching list when the 'Back to list' button" +
        " is clicked", function() {
        // arrange
        create_dataset_detail_controller();

        // act
        matching_ctrl_scope.$digest();
        matching_ctrl_scope.show_building_list = false;
        matching_ctrl_scope.back_to_list();

        // assertions
        expect(matching_ctrl_scope.show_building_list).toEqual(true);
    });

    it("should present an initial state with the matching buildings table",
        function() {
        // arrange
        create_dataset_detail_controller();

        // act
        matching_ctrl_scope.$digest();

        // assertions
        expect(matching_ctrl_scope.columns).toEqual([{ sort_column : 'pm_property_id' }]);
        expect(matching_ctrl_scope.number_matching_search).toEqual(1);
        expect(matching_ctrl_scope.number_returned).toEqual(1);
        expect(matching_ctrl_scope.num_pages).toEqual(1);
        expect(mock_buildging_services.get_PM_filter_by_counts).toHaveBeenCalled();
    });
    it("should match a building in the matching list", function() {
        // arrange
        create_dataset_detail_controller();
        var b1, b2;
        b2 = {
            id: 2,
            children: [],
            matched: false
        };
        b1 = {
            id: 1,
            children: [],
            matched: true,
            coparent: b2
        };

        // act
        matching_ctrl_scope.$digest();
        matching_ctrl_scope.toggle_match(b1);
        matching_ctrl_scope.$digest();

        // assertions
        expect(mock_buildging_services.save_match).toHaveBeenCalledWith(b1.id, b2.id, true);
        expect(mock_buildging_services.get_PM_filter_by_counts).toHaveBeenCalled();
        expect(b1.children[0]).toEqual(3);
    });

});
