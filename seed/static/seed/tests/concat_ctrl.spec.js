describe("controller: concat_modal_ctrl", function(){
    // globals set up and used in each test scenario
    var scope, controller, modal_state;
    var edit_ctrl, concat_modal_ctrl_scope, modalInstance, labels;
    var deleted_label, updated_label, mock_mapping_service, mock_matching_service;
    var global_step = 1;
    var global_dataset = {};

    // make the seed app available for each test
    // 'BE.seed' is created in TestFilters.html
    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function(
            $controller, $rootScope, $modal, urls, $q
        ) {
            controller = $controller;
            scope = $rootScope;
            concat_modal_ctrl_scope = $rootScope.$new();
            concat_modal_ctrl_scope.concat_columns = [];
            modal_state = "";
        }
    ));

    var mock_building_column_types = [
        'address1', 'city', 'state', 'postal_code'
    ];

    var mock_raw_columns = [
        {
            name: 'Address',
            suggestion: 'address1',
            confidence: 1,
            raw_data: [
                '234 Database way',
                '23444 Huh hwy',
                '23444 Huh hwy',
                '23444 Huh hwy',
                '1223 face pl.'
            ],
            is_concatenated: false,
            is_a_concat_parameter: false
        },
        {
            name: 'City',
            suggestion: 'city',
            confidence: 1,
            raw_data: [
                'Mega City', 'Mega City', 'Mega City', 'Mega City', 'Mega City',
            ],
            is_concatenated: false,
            is_a_concat_parameter: false
        },
        {
            name: 'Zip',
            suggestion: '',
            confidence: 0,
            raw_data: [
                '234233', '234233', '234233', '234233', '234233',
            ],
            is_concatenated: false,
            is_a_concat_parameter: false
        },
    ];

    // this is outside the beforeEach so it can be configured by each unit test
    function create_concat_modal_controller(){
        edit_ctrl = controller('concat_modal_ctrl', {
            $scope: concat_modal_ctrl_scope,
            $modalInstance: {
                close: function() {
                    modal_state = "close";
                },
                dismiss: function() {
                    modal_state = "dismiss";
                }
            },
            building_column_types: mock_building_column_types,
            raw_columns: mock_raw_columns,
        });
    }

    /*
     * Test scenarios
     */

    it("should close the modal when the close funtion is called", function() {
        // arrange
        create_concat_modal_controller();

        // act
        concat_modal_ctrl_scope.close_concat_modal();
        concat_modal_ctrl_scope.$digest();

        // assertions
        expect(modal_state).toBe("close");
    });

    it("should mangle scope appropriately during concatenation", function() {
        // arrange
        create_concat_modal_controller();

        // act
        concat_modal_ctrl_scope.$digest();

        // assertions
        expect(concat_modal_ctrl_scope.raw_columns.length).toBe(3);

        // arrange
        concat_modal_ctrl_scope.concat_columns =
            concat_modal_ctrl_scope.raw_columns.slice(0);
        concat_modal_ctrl_scope.raw_columns = [];

        // act
        concat_modal_ctrl_scope.$digest();
        concat_modal_ctrl_scope.save_concat();

        // assertions
        expect(concat_modal_ctrl_scope.raw_columns.length).toBe(1);
        expect(
            concat_modal_ctrl_scope.raw_columns[0].is_concatenated
        ).toEqual(true);
    });

    it("should modify the raw_data of our modified TCM correctly", function() {
        // arrange
        create_concat_modal_controller();

        // act
        concat_modal_ctrl_scope.$digest();

        // assertions
        expect(concat_modal_ctrl_scope.raw_columns.length).toBe(3);

        // arrange
        concat_modal_ctrl_scope.concat_columns =
            concat_modal_ctrl_scope.raw_columns.slice(0);
        concat_modal_ctrl_scope.raw_columns = [];

        // act
        concat_modal_ctrl_scope.$digest();
        concat_modal_ctrl_scope.save_concat();

        var expected_raw = [
            '234 Database way Mega City 234233',
            '23444 Huh hwy Mega City 234233',
            '23444 Huh hwy Mega City 234233',
            '23444 Huh hwy Mega City 234233',
            '1223 face pl. Mega City 234233'
        ];

        // assertions
        expect(
            concat_modal_ctrl_scope.raw_columns[0].raw_data
        ).toEqual(expected_raw);
    });
});
