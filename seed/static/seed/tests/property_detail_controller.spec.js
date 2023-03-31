/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
describe('controller: inventory_detail_controller', function () {

  // globals set up and used in each test scenario
  var ngFilter, ngLog, ngUrls;
  var controller, inventory_detail_controller_scope;
  var mock_inventory_service, state;
  var mock_uib_modal, mock_label_service, mock_label_payload;

  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $state, $uibModal, $log, $filter, $stateParams, $q, urls, label_service, inventory_service) {
      controller = $controller;
      state = $state;
      ngFilter = $filter;
      ngLog = $log;
      ngUrls = urls;
      mock_uib_modal = $uibModal;
      mock_label_service = label_service;

      inventory_detail_controller_scope = $rootScope.$new();

      // mock the inventory_service factory methods used in the controller
      // and return their promises
      mock_inventory_service = inventory_service;

      spyOn(mock_inventory_service, 'update_property')
        .andCallFake(function (view_id, property_state) {
          inventory_detail_controller_scope.item_state = property_state;
          return $q.resolve({
            status: 'success'
          });
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_inventory_detail_controller () {

    var fake_inventory_payload = {
      property: {
        id: 4,
        organization: 24,
        parent_property: '',
        inventory_documents: [
          {
            "id": 1,
            "file_type": "PDF",
            "created": "2022-04-10T19:35:58.448094-07:00",
            "file": "/media/inventory_documents/1-s2.0-S1364032115000672-main.pdf",
            "filename": "1-s2.0-S1364032115000672-main.pdf",
            "property": 4
          }
        ],
      },
      cycle: {
        created: '2016-08-02T16:38:22.925258Z',
        end: '2011-01-01T07:59:59Z',
        id: 1,
        name: '2010 Calendar Year',
        organization: 24,
        start: '2010-01-01T08:00:00Z',
        user: ''
      },
      taxlots: [{
        taxlot: {id: 2},
        cycle: {id: 1},
        state: {address_line_1: '123 Main St. LOT A'}
      }, {
        taxlot: {id: 3},
        cycle: {id: 1},
        state: {address_line_1: '123 Main St. LOT B'}
      }],
      state: {
        address_line_1: '123 Main St.',
        address_line_2: 'Top floor!',
        building_certification: '',
        building_count: '',
        building_home_energy_score_identifier: '',
        building_portfolio_manager_identifier: '477198',
        city: 'EnergyTown',
        conditioned_floor_area: '',
        energy_alerts: '',
        energy_score: 74,
        extra_data: {
          'National Median Site EUI (kBtu/ft2)': '120.3',
          'National Median Source EUI (kBtu/ft2)': '282.3',
          Organization: 'Acme Inc',
          'Parking - Gross Floor Area (ft2)': '89041',
          'Property Floor Area (Buildings And Parking) (ft2)': '139,835',
          'Total GHG Emissions (MtCO2e)': '2114.3',
          custom_id_1: '',
          prop_bs_id: 87941,
          prop_cb_id: 33315,
          record_created: '2016-07-27T15:52:11.879Z',
          record_modified: '2016-07-27T15:55:10.180Z',
          record_year_ending: '2010-12-31'
        },
        generation_date: '2013-09-27T18:41:00Z',
        gross_floor_area: '',
        id: 1048,
        jurisdiction_property_identifier: '',
        lot_number: '',
        occupied_floor_area: '',
        owner: '',
        owner_address: '',
        owner_city_state: '',
        owner_email: '',
        owner_postal_code: '',
        owner_telephone: '',
        pm_parent_property_id: '',
        postal_code: '10106-7162',
        property_name: '',
        property_notes: '',
        recent_sale_date: '',
        release_date: '2013-09-27T18:42:00Z',
        site_eui: 91.8,
        site_eui_weather_normalized: 89.0,
        source_eui: 215.5,
        source_eui_weather_normalized: '',
        space_alerts: '',
        state: 'Illinois',
        use_description: '',
        year_built: 1964,
        year_ending: ''
      },
      extra_data_keys: [
        'National Median Site EUI (kBtu/ft2)',
        'National Median Source EUI (kBtu/ft2)',
        'Organization',
        'Parking - Gross Floor Area (ft2)',
        'Property Floor Area (Buildings And Parking) (ft2)',
        'Total GHG Emissions (MtCO2e)',
        'custom_id_1',
        'prop_bs_id',
        'prop_cb_id',
        'record_created',
        'record_modified',
        'record_year_ending'
      ],
      changed_fields: {
        regular_fields: [
          'address_line_2',
          'site_eui',
          'source_eui'
        ],
        extra_data_fields: []
      },
      history: [{
        state: {
          address_line_1: '123 Main St.',
          address_line_2: 'Second floor',
          site_eui: 21,
          source_eui: 22,
          extra_data: {
            'National Median Site EUI (kBtu/ft2)': '120.3',
            'National Median Source EUI (kBtu/ft2)': '282.3',
            Organization: 'Acme Inc',
            'Parking - Gross Floor Area (ft2)': '89041',
            'Property Floor Area (Buildings And Parking) (ft2)': '139,835',
            'Total GHG Emissions (MtCO2e)': '2114.3',
            custom_id_1: '',
            prop_bs_id: 87941,
            prop_cb_id: 33315,
            record_created: '2016-07-27T15:52:11.879Z',
            record_modified: '2016-07-27T15:55:10.180Z',
            record_year_ending: '2010-12-31'
          }
        },
        changed_fields: {
          regular_fields: [
            'address_line_2',
            'site_eui',
            'source_eui'
          ],
          extra_data_fields: []
        },
        date_edited: '2016-07-26T15:55:10.180Z',
        source: 'UserEdit'
      }, {
        state: {
          address_line_1: '123 Main St.',
          address_line_2: 'Third floor',
          site_eui: 19,
          source_eui: 18,
          extra_data: {
            'National Median Site EUI (kBtu/ft2)': '120.3',
            'National Median Source EUI (kBtu/ft2)': '282.3',
            Organization: 'Acme Inc',
            'Parking - Gross Floor Area (ft2)': '89041',
            'Property Floor Area (Buildings And Parking) (ft2)': '139,835',
            'Total GHG Emissions (MtCO2e)': '2114.3',
            custom_id_1: '',
            prop_bs_id: 87941,
            prop_cb_id: 33315,
            record_created: '2016-07-27T15:52:11.879Z',
            record_modified: '2016-07-27T15:55:10.180Z',
            record_year_ending: '2010-12-31'
          }
        },
        changed_fields: {
          regular_fields: [],
          extra_data_fields: []
        },
        date_edited: '2016-07-25T15:55:10.180Z',
        source: 'ImportFile',
        filename: 'myfile.csv'
      }],
      status: 'success',
      message: ''
    };

    var fake_all_columns = [{
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
    }, {
      title: 'Address Line 1',
      sort_column: 'property_name',
      'class': '',
      title_class: '',
      type: 'string',
      field_type: 'building_information',
      sortable: true,
      checked: false
    }];

    var fake_derived_columns_payload = {
      derived_columns: [],
    };
    controller('inventory_detail_controller', {
      $state: state,
      $scope: inventory_detail_controller_scope,
      $uibModal: mock_uib_modal,
      $stateParams: {
        view_id: 4,
        inventory_type: 'properties'
      },
      $log: ngLog,
      $filter: ngFilter,
      urls: ngUrls,
      label_service: mock_label_service,
      inventory_service: mock_inventory_service,
      inventory_payload: fake_inventory_payload,
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
          taxlot_display_field: 'address_line_1',
        },
      },
      analyses_payload: {
        analyses: []
      },
      users_payload: {
        users: []
      },
      views_payload: {
        status:	"success",
        property_views: [],
      }
    });
  }


  /**
   * Test scenarios
   */

  it('should have a Property payload with correct object properties', function () {

    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.inventory.view_id).toBe(4);
    expect(inventory_detail_controller_scope.item_state.address_line_1).toBe('123 Main St.');

  });


  it('should make a copy of Property while making edits', function () {

    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.address_line_1 = 'ABC Main St.';

    // assertions
    expect(inventory_detail_controller_scope.item_copy.address_line_1).toBe('123 Main St.');

  });

  it('should restore enabled the edit fields if a user clicks edit', function () {

    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();

    // assertions
    expect(inventory_detail_controller_scope.edit_form_showing).toBe(true);

  });


  it('should restore the copy of Property state if a user clicks cancel', function () {

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


  it('should save the Property state when a user clicks the save button', function () {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.address_line_1 = 'ABC Main St.';
    inventory_detail_controller_scope.save_item();

    // assertions
    expect(mock_inventory_service.update_property)
      .toHaveBeenCalledWith(inventory_detail_controller_scope.inventory.view_id,
        inventory_detail_controller_scope.item_state);
    expect(inventory_detail_controller_scope.item_state.address_line_1).toEqual('ABC Main St.');
  });


  it('should hide certain Property properties, including ids and extra_data', function () {

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
