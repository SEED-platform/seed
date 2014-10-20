/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe("controller: mapping_controller", function(){
    // globals set up and used in each test scenario
    var mock_building_services, scope, controller, modal_state;
    var mapping_ctrl, mapping_ctrl_scope, modalInstance, labels;
    var timeout, mock_user_service, mock_search_service;



    // make the seed app available for each test
    // 'BE.seed' is created in TestFilters.html
    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function($controller, $rootScope, $modal, urls, $q, building_services, $timeout, user_service, search_service) {
            controller = $controller;
            scope = $rootScope;
            mapping_ctrl_scope = $rootScope.$new();
            modal_state = "";
            timeout = $timeout;
            mock_user_service = user_service;
            mock_search_service = search_service;

            spyOn(mock_user_service, 'set_default_columns')
                .andCallFake(function(mapped_columns){
                    return undefined;
                });
            spyOn(mock_search_service, 'search_buildings')
                .andCallFake(function(){
                    return [1,2,3];
                });
        }
    ));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_mapping_controller(){
        var mock_datasets = [
            {
                name: "DC 2013 data",
                last_modified: (new Date()).getTime(),
                last_modified_by: "john.s@buildingenergy.com",
                number_of_buildings: 89,
                id: 1
            },
            {
                name: "DC 2014 data",
                last_modified: (new Date()).getTime() -
                    1550 * 60 * 60 * 1000,
                last_modified_by: "gavin.m@buildingenergy.com",
                number_of_buildings: 70,
                id: 2
            }
        ];
        var fake_import_file_payload = {
            "status": "success",
            "import_file": {
                        file_name: "assessor_fun.csv",
                        last_modified: (new Date()).getTime(),
                        last_modified_by: "john.s@buildingenergy.com",
                        source_type: 'AssessorRaw',
                        dataset: mock_datasets[0],
                        id: 1
                    }
        };

        var mock_be_building_columns = [
            'pm_property_id',
            'property_name',
            'property_notes',
            'tax_lot_id',
            'gross_floor_area',
            'My New non-BEDES field'
        ];

        var mock_be_building_types = {
            'gross_floor_area': {
                unit_type: 'float',
                schema: 'BEDES'
            }
        };

        var mock_mapping_suggestions_payload = {
            'status': 'success',
            'suggested_column_mappings': {
                // key(django model attribute): [csv_header1, ... csv_header3]
                'property id': ['pm_property_id', 89],
                'lot number': ['tax_lot_id' , 54]
            },
            "building_columns": mock_be_building_columns,
            "building_column_types": mock_be_building_types
        };

        var mock_raw_column_names = [
            'property id',
            'property_name',
            'property_notes',
            'lot number',
            'lot size'
        ];

        var mock_first_five_rows = [];
        for (var i=0; i < 4; i++) {
            mock_first_five_rows.push({
                'property id': i,
                'property_name': 'Property ' + i,
                'property_notes': 'Nup.',
                'lot number': i * 2,
                'lot size': 454 * i
            });
        }

        mock_first_five_rows.push({
            'property id': '121L',
            'property_name': 'Inconsistent Property',
            'property_notes': 'N/A',
            'lot number': 'N/A',
            'lot size': 45
        });

        var raw_columns_payload = {
            "status": "success",
            "raw_columns": mock_raw_column_names
        };
        var first_five_rows_payload = {
            "status": "success",
            "first_five_rows": mock_first_five_rows
        };
        mapping_ctrl = controller('mapping_controller', {
            $scope: mapping_ctrl_scope,
            import_file_payload: fake_import_file_payload,
            suggested_mappings_payload: mock_mapping_suggestions_payload,
            raw_columns_payload: raw_columns_payload,
            first_five_rows_payload: first_five_rows_payload,
            all_columns: {fields: []},
            building_services: mock_building_services,
            $timeout: timeout
        });
    }

    /*
     * Test scenarios
     */

    it("should have a import_file_payload", function() {
        // arrange
        create_mapping_controller();

        // act
        mapping_ctrl_scope.$digest();

        // assertions
        expect(mapping_ctrl_scope.import_file.dataset.name).toBe("DC 2013 data");
    });

    it("should show suggested mappings and confidence", function() {
        // arrange
        create_mapping_controller();

        // act
        mapping_ctrl_scope.$digest();

        // assertions
        var raw_columns = mapping_ctrl_scope.raw_columns;
        var first_column = raw_columns[0];

        expect(first_column.confidence).toBe(89);
        expect(first_column.suggestion).toBe("Pm Property Id");
    });

    it("should show 'low', 'med', 'high', or '' confidence text", function() {
        // arrange
        create_mapping_controller();

        // act
        mapping_ctrl_scope.$digest();

        // assertions
        var raw_columns = mapping_ctrl_scope.raw_columns;
        var first_column = raw_columns[0];
        expect(first_column.confidence_text()).toBe("high");
        first_column.confidence = 70;
        expect(first_column.confidence_text()).toBe("med");
        first_column.confidence = 35;
        expect(first_column.confidence_text()).toBe("low");
        delete(first_column.confidence);
        expect(first_column.confidence_text()).toBe("");
    });

    it("should validate initial data", function() {
        create_mapping_controller();
        // act
        mapping_ctrl_scope.$digest();
        // assertions
        angular.forEach(mapping_ctrl_scope.raw_columns, function(rc) {
            if (rc.suggestion !== '' && typeof(rc.suggestion) !== "undefined") {
                expect(rc.validity).toBe('valid');
            }
        });
    });

    it("should invalidate bad suggestions", function() {
        // Simulate a change on the tcm, make it fail.
        create_mapping_controller();
        // act
        mapping_ctrl_scope.$digest();
        // assertions
        //
        // We change the suggested mapping for the "property name" column
        // to "gross_floor_area" (which validates as float) to
        // purposesly cause a failing change.
        mapping_ctrl_scope.raw_columns[1].suggestion = 'gross_floor_area';
        mapping_ctrl_scope.validate_data(mapping_ctrl_scope.raw_columns[1]);
        expect(mapping_ctrl_scope.raw_columns[1].validity).toBe('invalid');

    });

    it("should set td_class appropriately", function() {
        var tcm;

        create_mapping_controller();

        mapping_ctrl_scope.$digest();
        tcm = mapping_ctrl_scope.raw_columns[0];
        var good_val = mapping_ctrl_scope.set_td_class(
            tcm,
            tcm.raw_data[0]
        );

        // First raw column is mapped up as pm_property_id <-> property_id
        // Any kind of string will be valid.
        expect(good_val).toBe('success');

        // Now set it to one that expects float values.
        // Only one of these will *not* validate.
        mapping_ctrl_scope.raw_columns[0].suggestion = 'gross_floor_area';
        mapping_ctrl_scope.validate_data(mapping_ctrl_scope.raw_columns[0]);

        tcm = mapping_ctrl_scope.raw_columns[0];
        var warning_val = mapping_ctrl_scope.set_td_class(
            tcm,
            tcm.raw_data[4]
        );

        expect(warning_val).toBe('warning');

        // We don't want the warning style to be applied to neighboring cells
        // in the same row. Check that the cell next to our invalid one is
        // unstyled (undefined).
        tcm = mapping_ctrl_scope.raw_columns[0];
        var adjacent_val = mapping_ctrl_scope.set_td_class(
            tcm,
            tcm.raw_data[3]
        );

        expect(adjacent_val).toBe(undefined);

        // Now we're saying the suggestion is to not map.
        // Check that we don't have any class set for this row now.
        mapping_ctrl_scope.raw_columns[0].suggestion = '';
        mapping_ctrl_scope.validate_data(mapping_ctrl_scope.raw_columns[0]);

        tcm = mapping_ctrl_scope.raw_columns[0];
        var blank_val = mapping_ctrl_scope.set_td_class(
            tcm,
            tcm.raw_data[4]
        );

        expect(blank_val).toBe('');

    });

    it("should detect duplicates of mapped rows", function() {
        create_mapping_controller();
        mapping_ctrl_scope.$digest();

        // raw_columns[0] and raw_columns[3] should be the only mapped rows
        var column = mapping_ctrl_scope.raw_columns[3];
        var test_class = mapping_ctrl_scope.is_tcm_duplicate(
            column
        );

        expect(test_class).toBe(false);

        // Set the property_name tcm's suggestion to the same as
        // the property_id tcm (raw_columns[0])
        column.suggestion = 'Pm Property Id';

        test_class = mapping_ctrl_scope.is_tcm_duplicate(
            column
        );

        expect(test_class).toBe(true);

        // Since we mark both duplicates as duplicates, the other
        // TCM that has the 'pm_property_id' suggestion should also get
        // 'danger' as its duplicate class.
        var other_dup = mapping_ctrl_scope.is_tcm_duplicate(
            mapping_ctrl_scope.raw_columns[0]
        );
        expect(other_dup).toBe(true);

        // Shows that mapped_row is the sole determinant of
        // column ignoring
        column.mapped_row = false;

        test_class = mapping_ctrl_scope.is_tcm_duplicate(
            column
        );

        expect(test_class).toBe(false);

    });

    it("should ignore duplicates of unmapped rows", function() {
        create_mapping_controller();
        mapping_ctrl_scope.$digest();

        // raw_columns[0] and raw_columns[3] should be the only mapped rows
        var column = mapping_ctrl_scope.raw_columns[1];
        var test_class = mapping_ctrl_scope.is_tcm_duplicate(
            column
        );

        expect(test_class).toBe(false);

        // Set the property_name tcm's suggestion to the same as
        // the property_id tcm (raw_columns[0])
        column.suggestion = 'Pm Property Id';

        test_class = mapping_ctrl_scope.is_tcm_duplicate(
            column
        );

        expect(test_class).toBe(false);
    });

    it("should get mapped buildings", function() {
        // arrange
        create_mapping_controller();

        // act
        mapping_ctrl_scope.$digest();
        mapping_ctrl_scope.get_mapped_buildings();
        mapping_ctrl_scope.$digest();

        // assertions
        expect(mapping_ctrl_scope.search.search_buildings).toHaveBeenCalled();
        expect(mock_user_service.set_default_columns).toHaveBeenCalled();
    });

    it("should enbale the 'show & review buildings' button if duplicates are" +
        " not present", function() {
        // arrange
        create_mapping_controller();

        // act
        mapping_ctrl_scope.$digest();
        for (var i = mapping_ctrl_scope.raw_columns.length - 1; i >= 0; i--) {
            mapping_ctrl_scope.change(mapping_ctrl_scope.raw_columns[i]);
        }
        var duplicates_found = mapping_ctrl_scope.duplicates_present();

        // assertions
        expect(duplicates_found).toBe(false);
    });

    it("should disable the 'show & review buildings' button if duplicates " +
        "are present", function() {
        // arrange
        create_mapping_controller();

        // act
        mapping_ctrl_scope.$digest();
        for (var i = mapping_ctrl_scope.raw_columns.length - 1; i >= 0; i--) {
            mapping_ctrl_scope.raw_columns[i].suggestion = "pm_property_id";
            mapping_ctrl_scope.change(mapping_ctrl_scope.raw_columns[i]);
        }
        var duplicates_found = mapping_ctrl_scope.duplicates_present();

        // assertions
        expect(duplicates_found).toBe(true);
    });

    it("should get mappings in an API friendly way", function() {
        create_mapping_controller();
        mapping_ctrl_scope.$digest();
        var mappings = mapping_ctrl_scope.get_mappings();
        expect(mappings.length).toBe(5);
        expect(mappings[0]).toEqual(['Pm Property Id', 'property id']);
        // everything in between is empty since we we're using only
        // suggested mappings.
        expect(mappings[3]).toEqual(['Tax Lot Id', 'lot number']);
    });

    it("should show the 'STEP 2' tab when reviewing mappings", function() {
        // arrange
        create_mapping_controller();
        mapping_ctrl_scope.$digest();

        // act
        var mappings = mapping_ctrl_scope.get_mapped_buildings();

        // assert
        expect(mapping_ctrl_scope.tabs).toEqual({
            'one_active': false,
            'two_active': true,
            'three_active': false
        });
    });

    it("should show BEDES fields with a checkbox", function() {
        // arrange
        create_mapping_controller();

        // act
        mapping_ctrl_scope.$digest();

        // assert
        expect(mapping_ctrl_scope.is_suggestion_BEDES('gross_floor_area')).toBe(true);
        expect(mapping_ctrl_scope.is_suggestion_BEDES('Gross Floor Area')).toBe(true);
        expect(mapping_ctrl_scope.is_suggestion_BEDES('My New non-BEDES field')).toBe(false);
    });

});
