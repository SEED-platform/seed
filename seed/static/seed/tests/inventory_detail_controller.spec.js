/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

// Replaces building detail controller, will test later with both property and taxlot data too
describe('controller: inventory_detail_controller', function () {
  // globals set up and used in each test scenario
  var mockService, scope, controller, ngFilter, delete_called;
  var inventory_detail_controller, inventory_detail_controller_scope, modalInstance;
  var mock_building_services, mock_building, mock_default_columns;
  var mock_project_service;

  beforeEach(function () {
    module('BE.seed');
  });

  beforeEach(function () {
    module(function ($provide) {
      $provide.service('default_columns', function () {
        return {columns: []};
      });
    });
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(
    function ($controller,
              $rootScope,
              $uibModal,
              urls,
              $q,
              inventory_service,
              project_service,
              default_columns,
              $filter) {
      controller = $controller;
      scope = $rootScope;
      ngFilter = $filter;
      inventory_detail_controller_scope = $rootScope.$new();
      modal_item_state = '';
      delete_called = false;
      mock_default_columns = default_columns;


      // mock the inventory_service factory methods used in the controller
      // and return their promises
      mock_building_services = inventory_service;
      // mock_project_service = project_service;

      // spyOn(mock_project_service, 'get_project')
      //   .andCallFake(function (project_slug) {
      //     return $q.when({
      //       status: 'success',
      //       project: {
      //         id: 33,
      //         name: 'test project',
      //         slug: project_slug
      //       }
      //     });
      //   });
      spyOn(mock_building_services, 'update_property')
        .andCallFake(function (property_id, cycle_id, state) {
          mock_building = state;
          return $q.when({
            status: 'success'
          });
        });
    }
  ));

  // this is outside the beforeEach so it can be configured by each unit test
  function create_inventory_detail_controller () {
    var fake_building = {
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
    var fake_payload = {
      status: 'success',
      // properties: fake_building,
      state: fake_building,
      // imported_buildings: fake_imported_buildings,
      projects: [],
      cycle: {
        id: 2017
      },
      user_org_id: 42
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
      title: 'Tax Lot ID',
      sort_column: 'tax_lot_id',
      'class': 'is_aligned_right',
      title_class: '',
      type: 'link',
      field_type: 'building_information',
      sortable: true,
      checked: false,
      'static': false,
      link: true
    }, {
      title: 'Custom ID 1',
      sort_column: 'custom_id_1',
      'class': 'is_aligned_right whitespace',
      title_class: '',
      type: 'link',
      field_type: 'building_information',
      sortable: true,
      checked: false,
      'static': false,
      link: true
    }, {
      title: 'Property Name',
      sort_column: 'property_name',
      'class': '',
      title_class: '',
      type: 'string',
      field_type: 'building_information',
      sortable: true,
      checked: false
    }];
    inventory_detail_controller = controller('inventory_detail_controller', {
      $scope: inventory_detail_controller_scope,
      $stateParams: {
        cycle_id: 2017,
        inventory_id: 1,
        inventory_type: 'properties',
        project_id: 2
      },
      inventory_payload: fake_payload,
      columns: fake_all_columns,
      labels_payload: {
        audit_logs: []
      }
    });
  }

  /**
   * Test scenarios
   */

  it('should have an inventory payload', function () {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.cycle.id).toBe(2017);
    expect(inventory_detail_controller_scope.item_state.id).toBe(511);
    expect(inventory_detail_controller_scope.inventory.id).toBe(1);
    // expect(inventory_detail_controller_scope.imported_buildings[0].id).toBe(2);
  });


  it('should make a copy of building while making edits', function () {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.on_edit();
    inventory_detail_controller_scope.item_state.gross_floor_area = 43214;

    // assertions
    expect(inventory_detail_controller_scope.item_copy.gross_floor_area)
      .toBe(123456);
  });
  it('should restore the copy of building if a user clicks cancel',
    function () {
      // arrange
      create_inventory_detail_controller();

      // act
      inventory_detail_controller_scope.$digest();
      inventory_detail_controller_scope.on_edit();
      inventory_detail_controller_scope.item_state.gross_floor_area = 43214;
      inventory_detail_controller_scope.on_cancel();

      // assertions
      expect(inventory_detail_controller_scope.item_state.gross_floor_area)
        .toBe(123456);
      expect(inventory_detail_controller_scope.edit_form_showing).toBe(false);
    });
  it('should save a building when a user clicks the save button', function () {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();
    inventory_detail_controller_scope.make_copy_before_edit();
    inventory_detail_controller_scope.item_state.gross_floor_area = 43214;
    inventory_detail_controller_scope.on_save();
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(mock_building_services.update_property)
      .toHaveBeenCalledWith(1, 2017, {gross_floor_area: 43214});
    expect(mock_building.gross_floor_area).toEqual(43214);
  });

  it('should set only building attribute to master, not ids or children', function () {
    // arrange
    create_inventory_detail_controller();

    // act
    inventory_detail_controller_scope.$digest();

    // assertions
    expect(inventory_detail_controller_scope.is_valid_data_column_key('id')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('pk')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('pk_source')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key(' extra_data ')).toEqual(false);
    expect(inventory_detail_controller_scope.is_valid_data_column_key('gross_floor_area'))
      .toEqual(true);
  });

  it('should display Floor Areas with number', function () {
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

  // I don't think the idea of active project is still used....
  // it('should highlight the active project', function() {
  //     // arrange
  //     create_inventory_detail_controller();

  //     // act
  //     inventory_detail_controller_scope.$digest();

  //     // assertions
  //     expect(inventory_detail_controller_scope.is_active_project({id:33}))
  //     .toBe(true);
  //     expect(inventory_detail_controller_scope.is_active_project({id:34}))
  //     .toBe(false);
  //     inventory_detail_controller_scope.project = undefined;
  //     expect(inventory_detail_controller_scope.is_active_project({id:34}))
  //     .toBe(false);
  // });

  // it('should show a project or buildings breadcrumb', function() {
  //     // arrange
  //     create_inventory_detail_controller();

  //     // act
  //     inventory_detail_controller_scope.$digest();
  //     inventory_detail_controller_scope.user.project_slug = 'project_1';

  //     // assertions
  //     expect(inventory_detail_controller_scope.is_project()).toEqual(true);
  //     inventory_detail_controller_scope.user.project_slug = undefined;
  //     expect(inventory_detail_controller_scope.is_project()).toEqual(false);

  // });
  // it('should show the default projects table if a user has no compliance' +
  //     ' projects', function() {
  //     // arrange
  //     create_inventory_detail_controller();

  //     // act
  //     inventory_detail_controller_scope.$digest();

  //     // assertions
  //     expect(inventory_detail_controller_scope.user.has_projects()).toEqual(false);
  //     inventory_detail_controller_scope.projects = [{id: 1, name: 'a'}];
  //     expect(inventory_detail_controller_scope.user.has_projects()).toEqual(true);

  // });

  //FIXIT - do these have an equiv?
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
