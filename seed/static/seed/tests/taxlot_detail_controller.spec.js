/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: taxlot_detail_controller', function(){

    // globals set up and used in each test scenario
    var scope, controller, ngFilter, delete_called, ngLog, ngUrls;
    var taxlot_detail_ctrl, taxlot_detail_ctrl_scope;
    var mock_property_taxlot_service, mock_taxlot, mock_default_taxlot_columns;
    var mock_uib_modal, mock_label_helper_service;

    beforeEach(function() {
        module('BE.seed');
    });

    beforeEach(function(){
        module(function($provide){
            $provide.service('default_taxlot_columns', function() {
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
          default_taxlot_columns
          ) {
            controller = $controller;
            scope = $rootScope;
            ngFilter = $filter;
            ngLog = $log;
            ngUrls = urls;
            mock_uib_modal = $uibModal;
            mock_label_helper_service = label_helper_service;

            taxlot_detail_ctrl_scope = $rootScope.$new();
            modal_state = '';
            delete_called = false;

            // Start with no default taxlot columns
            mock_default_taxlot_columns = default_taxlot_columns;

            // mock the property_taxlot_service factory methods used in the controller
            // and return their promises
            mock_property_taxlot_service = property_taxlot_service;

            spyOn(mock_property_taxlot_service, 'update_taxlot')
                .andCallFake(function (taxlot_id, cycle_id, taxlot_state){
                    taxlot_detail_ctrl_scope.item_state = taxlot_state;
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
    function create_taxlot_detail_controller(){

        var fake_taxlot = {
            id: 123,
            cycle: {
                id: 2
            },
            state: {
                address_line_1: "123 Main St.",
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

        var fake_all_taxlot_columns = [
            //TODO need more example taxlot columns
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
        taxlot_detail_ctrl = controller('taxlot_detail_controller', {
            $controller: controller,
            $scope: taxlot_detail_ctrl_scope,
            $uibModal: mock_uib_modal,
            $log : ngLog,
            $filter: ngFilter,
            urls: ngUrls,
            label_helper_service: mock_label_helper_service,
            property_taxlot_service: mock_property_taxlot_service,
            taxlot_payload: fake_taxlot,
            default_taxlot_columns: mock_default_taxlot_columns,
            all_taxlot_columns: {
                fields: fake_all_taxlot_columns
            }
        });
    }


    /*
     * Test scenarios
     */

    it('should have a TaxLot payload with correct object properties', function() {

        // arrange
        create_taxlot_detail_controller();

        // act
        taxlot_detail_ctrl_scope.$digest();

        // assertions
        expect(taxlot_detail_ctrl_scope.taxlot.id).toBe(123);
        expect(taxlot_detail_ctrl_scope.taxlot.cycle.id).toBe(2);
        expect(taxlot_detail_ctrl_scope.item_state.address_line_1).toBe("123 Main St.");

    });


    it('should make a copy of TaxLot state while making edits', function() {

        // arrange
        create_taxlot_detail_controller();

        // act
        taxlot_detail_ctrl_scope.$digest();
        taxlot_detail_ctrl_scope.on_edit();
        taxlot_detail_ctrl_scope.item_state.address_line_1 = "ABC Main St.";

        // assertions
        expect(taxlot_detail_ctrl_scope.item_copy.address_line_1).toBe("123 Main St.");

    });

    it('should restore enabled the edit fields if a user clicks edit', function() {

        // arrange
        create_taxlot_detail_controller();

        // act
        taxlot_detail_ctrl_scope.$digest();
        taxlot_detail_ctrl_scope.on_edit();

        // assertions
        expect(taxlot_detail_ctrl_scope.edit_form_showing).toBe(true);

    });



    it('should restore the copy of TaxLot state if a user clicks cancel', function() {

        // arrange
        create_taxlot_detail_controller();

        // act
        taxlot_detail_ctrl_scope.$digest();
        taxlot_detail_ctrl_scope.on_edit();
        taxlot_detail_ctrl_scope.item_state.address_line_1 = "ABC Main St.";
        taxlot_detail_ctrl_scope.on_cancel();

        // assertions
        expect(taxlot_detail_ctrl_scope.item_state.address_line_1).toBe("123 Main St.");
        expect(taxlot_detail_ctrl_scope.edit_form_showing).toBe(false);

    });


    it('should save the TaxLot state when a user clicks the save button', function() {
        // arrange
        create_taxlot_detail_controller();

        // act
        taxlot_detail_ctrl_scope.$digest();
        taxlot_detail_ctrl_scope.on_edit();
        taxlot_detail_ctrl_scope.item_state.address_line_1 = "ABC Main St.";
        taxlot_detail_ctrl_scope.on_save();

        // assertions
        expect(mock_property_taxlot_service.update_taxlot)
        .toHaveBeenCalledWith(  taxlot_detail_ctrl_scope.taxlot.id,
                                taxlot_detail_ctrl_scope.taxlot.cycle.id,
                                taxlot_detail_ctrl_scope.item_state);
        expect(taxlot_detail_ctrl_scope.item_state.address_line_1).toEqual("ABC Main St.");
    });


    it('should hide certain TaxLot properties, including ids and extra_data', function() {

        // arrange
        create_taxlot_detail_controller();

        // act
        taxlot_detail_ctrl_scope.$digest();

        // assertions
        expect(taxlot_detail_ctrl_scope.is_valid_data_column_key('id')).toEqual(false);
        expect(taxlot_detail_ctrl_scope.is_valid_data_column_key('pk')).toEqual(false);
        expect(taxlot_detail_ctrl_scope.is_valid_data_column_key('pk_source')).toEqual(false);
        expect(taxlot_detail_ctrl_scope.is_valid_data_column_key('extra_data ')).toEqual(false);
        expect(taxlot_detail_ctrl_scope.is_valid_data_column_key('address_line_1')).toEqual(true);

    });



});
