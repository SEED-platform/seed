/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: inventory_detail_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let ngFilter;
  let ngLog;
  let ngUrls;
  let inventory_detail_controller_scope;
  let mock_inventory_service;
  let state;
  let mock_uib_modal;
  let mock_label_service;
  let mock_label_payload;

  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $state, $uibModal, $log, $filter, $stateParams, $q, urls, label_service, inventory_service) => {
      controller = $controller;
      state = $state;
      ngFilter = $filter;
      ngLog = $log;
      ngUrls = urls;
      mock_uib_modal = $uibModal;
      mock_label_service = label_service;
      mock_label_service = label_service;

      inventory_detail_controller_scope = $rootScope.$new();

      // mock the inventory_service factory methods used in the controller
      // and return their promises
      mock_inventory_service = inventory_service;

      spyOn(mock_inventory_service, 'update_taxlot').andCallFake((view_id, taxlot_state) => {
        inventory_detail_controller_scope.item_state = taxlot_state;
        return $q.resolve({
          status: 'success'
        });
      });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_inventory_detail_controller() {
    const fake_taxlot_payload = {
      taxlot: {
        id: 4,
        organization: 24
      },
      cycle: {
        created: '2016-08-02T16:38:22.925258Z',
        end: '2011-01-01',
        id: 1,
        name: '2010 Calendar Year',
        organization: 24,
        start: '2010-01-01',
        user: ''
      },
      properties: [
        {
          property: { id: 2 },
          cycle: { id: 1 },
          state: { address_line_1: '123 Main St. Bldg 1' }
        },
        {
          property: { id: 3 },
          cycle: { id: 1 },
          state: { address_line_1: '123 Main St. Bldg 2' }
        }
      ],
      state: {
        address_line_1: '123 Main St.',
        address_line_2: 'the newest value!',
        state: 'Illinois',
        extra_data: {
          some_extra_data_field_1: '1',
          some_extra_data_field_2: '2',
          some_extra_data_field_3: '3',
          some_extra_data_field_4: '4'
        }
      },
      extra_data_keys: ['some_extra_data_field_1', 'some_extra_data_field_2', 'some_extra_data_field_3', 'some_extra_data_field_4'],
      changed_fields: {
        regular_fields: ['address_line_2'],
        extra_data_fields: []
      },
      history: [
        {
          state: {
            address_line_1: '123 Main St.',
            address_line_2: 'newer value',
            state: 'Illinois',
            extra_data: {
              some_extra_data_field_1: '1',
              some_extra_data_field_2: '2',
              some_extra_data_field_3: '3',
              some_extra_data_field_4: '4'
            }
          },
          changed_fields: {
            regular_fields: ['address_line_2'],
            extra_data_fields: []
          },
          date_edited: '2016-07-26T15:55:10.180Z',
          source: 'UserEdit'
        },
        {
          state: {
            address_line_1: '123 Main St.',
            address_line_2: 'old value',
            state: 'Illinois',
            extra_data: {
              some_extra_data_field_1: '1',
              some_extra_data_field_2: '2',
              some_extra_data_field_3: '3',
              some_extra_data_field_4: '4'
            }
          },
          changed_fields: {
            regular_fields: [],
            extra_data_fields: []
          },
          date_edited: '2016-07-25T15:55:10.180Z',
          source: 'ImportFile',
          filename: 'myfile.csv'
        }
      ],
      status: 'success'
    };

    // TODO need more example taxlot columns
    const fake_all_columns = [
      {
        title: 'Address Line 1',
        sort_column: 'property_name',
        class: '',
        title_class: '',
        type: 'string',
        field_type: 'building_information',
        sortable: true,
        checked: false
      }
    ];

    const fake_derived_columns_payload = {
      derived_columns: []
    };
    controller('inventory_detail_controller', {
      $state: state,
      $scope: inventory_detail_controller_scope,
      $uibModal: mock_uib_modal,
      $stateParams: {
        view_id: 4,
        inventory_type: 'taxlots'
      },
      $log: ngLog,
      $filter: ngFilter,
      urls: ngUrls,
      label_service: mock_label_service,
      inventory_service: mock_inventory_service,
      inventory_payload: fake_taxlot_payload,
      columns: {
        fields: fake_all_columns
      },
      derived_columns_payload: fake_derived_columns_payload,
      profiles: [],
      current_profile: undefined,
      labels_payload: mock_label_payload,
      organization_payload: {
        organization: {
          id: 1,
          display_decimal_places: 2,
          property_display_field: 'address_line_1',
          taxlot_display_field: 'address_line_1'
        }
      },
      analyses_payload: {
        analyses: []
      },
      elements_payload: [],
      tkbl_payload: [],
      uniformat_payload: {},
      views_payload: {
        status: 'success',
        taxlot_views: []
      }
    });
  }

  /**
   * Test scenarios
   */

  it('should have a TaxLot payload with correct object properties', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.inventory.view_id).toBe(4);
    expect(inventory_detail_controller_scope.item_state.address_line_1).toBe('123 Main St.');
  });

  it('should make a copy of TaxLot state while making edits', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.address_line_1 = 'ABC Main St.';

    // assertions
    expect(inventory_detail_controller_scope.item_copy.address_line_1).toBe('123 Main St.');
  });

  it('should restore enabled the edit fields if a user clicks edit', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();

    // assertions
    expect(inventory_detail_controller_scope.edit_form_showing).toBe(true);
  });

  it('should restore the copy of TaxLot state if a user clicks cancel', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.address_line_1 = 'ABC Main St.';
    inventory_detail_controller_scope.on_cancel();

    // assertions
    expect(inventory_detail_controller_scope.item_state.address_line_1).toBe('123 Main St.');
    expect(inventory_detail_controller_scope.edit_form_showing).toBe(false);
  });

  it('should save the TaxLot state when a user clicks the save button', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.address_line_1 = 'ABC Main St.';
    inventory_detail_controller_scope.save_item();

    // assertions
    expect(mock_inventory_service.update_taxlot).toHaveBeenCalledWith(inventory_detail_controller_scope.inventory.view_id, inventory_detail_controller_scope.item_state);
    expect(inventory_detail_controller_scope.item_state.address_line_1).toEqual('ABC Main St.');
  });

  it('should hide certain TaxLot properties, including ids and extra_data', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.is_valid_data_column_key('id')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('pk')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('pk_source')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('extra_data ')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('address_line_1')).toEqual(true);
  });
});
