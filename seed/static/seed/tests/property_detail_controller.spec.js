/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: property_detail_controller', function(){

    // globals set up and used in each test scenario
    var scope, controller, ngFilter, delete_called, ngLog, ngUrls;
    var property_detail_ctrl, property_detail_ctrl_scope;
    var mock_property_taxlot_service, mock_property, mock_default_property_columns;
    var mock_uib_modal, mock_label_helper_service;

    beforeEach(function() {
        module('BE.seed');
    });

    beforeEach(function(){
        module(function($provide){
            $provide.service('default_property_columns', function() {
                return { columns: [] };
            });
        });
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function(
          $controller,
          $rootScope,
          $uibModal,
          $log,
          $filter,
          urls,
          $q,
          label_helper_service,
          property_taxlot_service,
          default_property_columns
          ) {
            controller = $controller;
            scope = $rootScope;
            ngFilter = $filter;
            ngLog = $log;
            ngUrls = urls;
            mock_uib_modal = $uibModal;
            mock_label_helper_service = label_helper_service;

            property_detail_ctrl_scope = $rootScope.$new();
            modal_state = '';
            delete_called = false;

            // Start with no default property columns
            mock_default_property_columns = default_property_columns;

            // mock the property_taxlot_service factory methods used in the controller
            // and return their promises
            mock_property_taxlot_service = property_taxlot_service;

            spyOn(mock_property_taxlot_service, 'update_property')
                .andCallFake(function (property_id, cycle_id, property_state){
                    property_detail_ctrl_scope.item_state = property_state;
                    return $q.when(
                        {
                            status: 'success'
                        }
                    );
                }
            );
        }
    ));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_property_detail_controller(){

        var fake_property = {
            id: 511,
            cycle: {
                id: 2
            },
            state: {
                address_line_1: "123 Main St.",
                gross_floor_area: 123456,
                gross_floor_area_source: 2,
                city: 'DC',
                city_source: 4,
                tax_lot_id: '11/22',
                tax_lot_id_source: 3,
                extra_data: {
                    'some other key': 12344,
                    'some other key that is not in a parent': 223
                },
                created: 'at some point'
            }
        };

        var fake_all_property_columns = [
            {
                title: 'PM Property ID',
                sort_column: 'pm_property_id',
                'class': 'is_aligned_right',
                title_class: '',
                type: 'link',
                field_type: 'building_information',
                sortable: true,
                checked: false,
                'static': false,
                link: true
            },
            {
                title: 'Address Line 1',
                sort_column: 'property_name',
                'class': '',
                title_class: '',
                type: 'string',
                field_type: 'building_information',
                sortable: true,
                checked: false
            }
        ];
        property_detail_ctrl = controller('property_detail_controller', {
            $controller: controller,
            $scope: property_detail_ctrl_scope,
            $uibModal: mock_uib_modal,
            $log : ngLog,
            $filter: ngFilter,
            urls: ngUrls,
            label_helper_service: mock_label_helper_service,
            property_taxlot_service: mock_property_taxlot_service,
            property_payload: fake_property,
            default_property_columns: mock_default_property_columns,
            all_property_columns: {
                fields: fake_all_property_columns
            }
        });
    }


    /*
     * Test scenarios
     */

    it('should have a Property payload with correct object properties', function() {

        // arrange
        create_property_detail_controller();

        // act
        property_detail_ctrl_scope.$digest();

        // assertions
        expect(property_detail_ctrl_scope.property.id).toBe(511);
        expect(property_detail_ctrl_scope.property.cycle.id).toBe(2);
        expect(property_detail_ctrl_scope.item_state.address_line_1).toBe("123 Main St.");

    });


    it('should make a copy of Property while making edits', function() {

        // arrange
        create_property_detail_controller();

        // act
        property_detail_ctrl_scope.$digest();
        property_detail_ctrl_scope.on_edit();
        property_detail_ctrl_scope.item_state.address_line_1 = "ABC Main St.";

        // assertions
        expect(property_detail_ctrl_scope.item_copy.address_line_1).toBe("123 Main St.");

    });

    it('should restore enabled the edit fields if a user clicks edit', function() {

        // arrange
        create_property_detail_controller();

        // act
        property_detail_ctrl_scope.$digest();
        property_detail_ctrl_scope.on_edit();

        // assertions
        expect(property_detail_ctrl_scope.edit_form_showing).toBe(true);

    });



    it('should restore the copy of Property state if a user clicks cancel', function() {

        // arrange
        create_property_detail_controller();

        // act
        property_detail_ctrl_scope.$digest();
        property_detail_ctrl_scope.on_edit();
        property_detail_ctrl_scope.item_state.address_line_1 = "ABC Main St.";
        property_detail_ctrl_scope.on_cancel();

        // assertions
        expect(property_detail_ctrl_scope.item_state.address_line_1).toBe("123 Main St.");
        expect(property_detail_ctrl_scope.edit_form_showing).toBe(false);

    });


    it('should save the Property state when a user clicks the save button', function() {
        // arrange
        create_property_detail_controller();

        // act
        property_detail_ctrl_scope.$digest();
        property_detail_ctrl_scope.on_edit();
        property_detail_ctrl_scope.item_state.address_line_1 = "ABC Main St.";
        property_detail_ctrl_scope.on_save();

        // assertions
        expect(mock_property_taxlot_service.update_property)
        .toHaveBeenCalledWith(  property_detail_ctrl_scope.property.id,
                                property_detail_ctrl_scope.property.cycle.id,
                                property_detail_ctrl_scope.item_state);
        expect(property_detail_ctrl_scope.item_state.address_line_1).toEqual("ABC Main St.");
    });


    it('should hide certain Property properties, including ids and extra_data', function() {

        // arrange
        create_property_detail_controller();

        // act
        property_detail_ctrl_scope.$digest();

        // assertions
        expect(property_detail_ctrl_scope.is_valid_data_column_key('id')).toEqual(false);
        expect(property_detail_ctrl_scope.is_valid_data_column_key('pk')).toEqual(false);
        expect(property_detail_ctrl_scope.is_valid_data_column_key('pk_source')).toEqual(false);
        expect(property_detail_ctrl_scope.is_valid_data_column_key('extra_data ')).toEqual(false);
        expect(property_detail_ctrl_scope.is_valid_data_column_key('address_line_1')).toEqual(true);

    });



});
