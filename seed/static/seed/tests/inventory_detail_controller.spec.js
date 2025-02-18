/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */

// Replaces building detail controller, will test later with both property and taxlot data too
describe('controller: inventory_detail_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let inventory_detail_controller_scope;
  let mock_building_service;
  let mock_building;

  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $uibModal, urls, $q, inventory_service) => {
      controller = $controller;
      inventory_detail_controller_scope = $rootScope.$new();

      // mock the inventory_service factory methods used in the controller
      // and return their promises
      mock_building_service = inventory_service;

      spyOn(mock_building_service, 'update_property').andCallFake((view_id, state) => {
        mock_building = state;
        return $q.resolve({
          status: 'success'
        });
      });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_inventory_detail_controller() {
    const fake_building = {
      id: 511,
      pk: 511,
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
    };
    // var fake_imported_buildings = [
    //     {
    //         id: 2,
    //         pk: 2,
    //         gross_floor_area: 123456,
    //         gross_floor_area_source: null,
    //         city: 'Washington, DC',
    //         city_source: null,
    //         extra_data: {
    //             'some other key': 123,
    //             'some other key that is not in a child': 333,
    //             'some floor area': 444
    //         },
    //         extra_data_sources: {
    //             'some other key': null,
    //             'some other key that is not in a child': 111,
    //             'some floor area': 444
    //         },
    //         created: 'test'
    //     },
    //     {
    //         id: 3,
    //         pk: 3,
    //         gross_floor_area: 2111111,
    //         gross_floor_area_source: null,
    //         city: 'Washington',
    //         city_source: null,
    //         tax_lot_id: '11/22',
    //         tax_lot_id_source: null,
    //         extra_data: {
    //             'make it four': 4
    //         },
    //         extra_data_sources: {
    //             'make it four': null
    //         }
    //     }, {
    //         id: 4,
    //         pk: 4,
    //         gross_floor_area: 2111111,
    //         gross_floor_area_source: null,
    //         city: 'Washington',
    //         city_source: null,
    //         tax_lot_id: '11/22',
    //         tax_lot_id_source: null,
    //         extra_data: {
    //             'make it four': 5
    //         },
    //         extra_data_sources: {
    //             'make it four': null
    //         }
    //     }
    // ];
    const fake_payload = {
      status: 'success',
      // properties: fake_building,
      state: fake_building,
      // imported_buildings: fake_imported_buildings,
      cycle: {
        id: 2017
      },
      user_org_id: 42,
      property: {
        inventory_documents: []
      }
    };
    const fake_all_columns = [
      {
        title: 'PM Property ID',
        sort_column: 'pm_property_id',
        class: 'is_aligned_right',
        title_class: '',
        type: 'link',
        field_type: 'building_information',
        sortable: true,
        checked: false,
        static: false,
        link: true
      },
      {
        title: 'Tax Lot ID',
        sort_column: 'tax_lot_id',
        class: 'is_aligned_right',
        title_class: '',
        type: 'link',
        field_type: 'building_information',
        sortable: true,
        checked: false,
        static: false,
        link: true
      },
      {
        title: 'Custom ID 1',
        sort_column: 'custom_id_1',
        class: 'is_aligned_right whitespace',
        title_class: '',
        type: 'link',
        field_type: 'building_information',
        sortable: true,
        checked: false,
        static: false,
        link: true
      },
      {
        title: 'Property Name',
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
      $scope: inventory_detail_controller_scope,
      $stateParams: {
        view_id: 1,
        inventory_type: 'properties'
      },
      inventory_payload: fake_payload,
      columns: fake_all_columns,
      derived_columns_payload: fake_derived_columns_payload,
      profiles: [],
      current_profile: undefined,
      labels_payload: {
        audit_logs: []
      },
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
        property_views: []
      }
    });
  }

  /**
   * Test scenarios
   */

  it('should have an inventory payload', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.item_state.id).toBe(511);
    expect(inventory_detail_controller_scope.inventory.view_id).toBe(1);
    // expect(inventory_detail_controller_scope.imported_buildings[0].id).toBe(2);
  });

  it('should make a copy of building while making edits', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.gross_floor_area = 43214;

    // assertions
    expect(inventory_detail_controller_scope.item_copy.gross_floor_area).toBe(123456);
  });

  it('should restore the copy of building if a user clicks cancel', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.gross_floor_area = 43214;
    inventory_detail_controller_scope.on_cancel();

    // assertions
    expect(inventory_detail_controller_scope.item_state.gross_floor_area).toBe(123456);
    expect(inventory_detail_controller_scope.edit_form_showing).toBe(false);
  });

  it('should save a building when a user clicks the save button', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.make_copy_before_edit();
    inventory_detail_controller_scope.item_state.gross_floor_area = 43214;
    inventory_detail_controller_scope.save_item();
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(mock_building_service.update_property).toHaveBeenCalledWith(1, { gross_floor_area: 43214 });
    expect(mock_building.gross_floor_area).toEqual(43214);
  });

  it('should set only building attribute to master, not ids or children', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.is_valid_data_column_key('id')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('pk')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('pk_source')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key(' extra_data ')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('gross_floor_area')).toEqual(true);
  });

  it('should display Floor Areas with number', () => {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.get_number('')).toEqual(0);
    expect(inventory_detail_controller_scope.get_number('123,123,123')).toEqual(123123123);
    expect(inventory_detail_controller_scope.get_number('123,123,123.123')).toEqual(123123123.123);
    expect(inventory_detail_controller_scope.get_number('-123,123,123')).toEqual(-123123123);
    expect(inventory_detail_controller_scope.get_number(-123123123)).toEqual(-123123123);
  });

  // Test doesn't make sense anymore:
  // it('should display all the data within all the buildings', function() {
  //     // arrange
  //     create_inventory_detail_controller();
  //     var keys;

  //     // act
  //     inventory_detail_controller_scope.$digest();

  //     // assertions
  //     var edc = inventory_detail_controller_scope.columns;

  //     // should not duplicate keys
  //     expect(edc.length).toEqual(8);
  //     keys = edc.map(function ( d ) {
  //         return d.key;
  //     });
  //     expect(keys.indexOf('make it four')).toEqual(4);
  // });

  // FIXIT - do these have an equiv?
  // it('should set a field as source when clicked', function() {
  //     // arrange
  //     create_inventory_detail_controller();

  //     // act
  //     inventory_detail_controller_scope.$digest();
  //     inventory_detail_controller_scope.imported_buildings[0].is_master = true;
  //     expect(inventory_detail_controller_scope.building.gross_floor_area_source)
  //       .not.toEqual(inventory_detail_controller_scope.building.id);
  //     inventory_detail_controller_scope.set_self_as_source('gross_floor_area');
  //     inventory_detail_controller_scope.set_self_as_source('some other key', true);
  //     inventory_detail_controller_scope.$digest();

  //     // assertions
  //     expect(inventory_detail_controller_scope.building.gross_floor_area_source)
  //       .toEqual(inventory_detail_controller_scope.building.id);
  //     expect(inventory_detail_controller_scope.imported_buildings[0].is_master)
  //       .toEqual(false);
  // });

  // it('should set a column as the dominant source when clicked', function() {
  //     // arrange
  //     create_inventory_detail_controller();

  //     // act
  //     inventory_detail_controller_scope.$digest();
  //     inventory_detail_controller_scope.imported_buildings[1].is_master = true;
  //     inventory_detail_controller_scope.make_source_default(
  //         inventory_detail_controller_scope.imported_buildings[0]);
  //     inventory_detail_controller_scope.$digest();

  //     // assertions
  //     var b = inventory_detail_controller_scope.building,
  //         i = inventory_detail_controller_scope.imported_buildings[0],
  //         i_other = inventory_detail_controller_scope.imported_buildings[1];

  //     expect(b.gross_floor_area_source).toEqual(i.id);
  //     expect(b.id).not.toEqual(i.id);
  //     expect(b.pk).not.toEqual(i.id);
  //     expect(b.city).toEqual(i.city);
  //     expect(b.city_source).toEqual(i.id);
  //     expect(b.tax_lot_id).toEqual('11/22');
  //     expect(b.tax_lot_id_source).toEqual(i_other.id);
  //     expect(b.extra_data['some other key']).toEqual(123);
  //     expect(b.extra_data_sources['some other key']).toEqual(i.id);
  //     expect(b.extra_data['some other key that is not in a child']).toEqual(333);
  //     expect(b.extra_data_sources['some other key that is not in a child']).toEqual(i.id);
  //     expect(b.extra_data['some other key that is not in a parent']).toEqual(223);
  //     expect(b.extra_data_sources['some other key that is not in a parent']).toEqual(i_other.id);
  //     expect(b.created).toEqual('at some point');

  //     expect(i.is_master).toEqual(true);
  //     expect(i_other.is_master).toEqual(false);
  // });

  // it('should set the master building value when parent\'s value is clicked',
  //     function() {
  //     // arrange
  //     create_inventory_detail_controller();

  //     // act
  //     inventory_detail_controller_scope.$digest();
  //     inventory_detail_controller_scope.imported_buildings[1].is_master = true;
  //     inventory_detail_controller_scope.set_building_attribute(
  //         inventory_detail_controller_scope.imported_buildings[0], 'city');
  //     inventory_detail_controller_scope.set_building_attribute(
  //         inventory_detail_controller_scope.imported_buildings[0], 'some other key', true);
  //     inventory_detail_controller_scope.$digest();

  //     // assertions
  //     var b = inventory_detail_controller_scope.building,
  //         i = inventory_detail_controller_scope.imported_buildings[0],
  //         i_other = inventory_detail_controller_scope.imported_buildings[1];

  //     expect(b.id).not.toEqual(i.id);
  //     expect(b.pk).not.toEqual(i.id);
  //     expect(b.city).toEqual(i.city);
  //     expect(b.city_source).toEqual(i.id);
  //     expect(b.tax_lot_id).toEqual('11/22');
  //     expect(b.tax_lot_id_source).toEqual(i_other.id);
  //     expect(b.extra_data['some other key']).toEqual(123);
  //     expect(b.extra_data_sources['some other key']).toEqual(i.id);

  //     expect(i.is_master).toEqual(false);
  //     expect(i_other.is_master).toEqual(false);
  // });

  // it('should display Floor Areas', function() {
  //     // arrange
  //     create_inventory_detail_controller();

  //     // act
  //     inventory_detail_controller_scope.$digest();
  //     inventory_detail_controller_scope.$digest();

  //     // assertions
  //     var area_fields = inventory_detail_controller_scope.floor_area_fields;
  //     expect(area_fields.length).toEqual(1);
  // });
});
