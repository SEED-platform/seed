/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: mapping_controller', function () {
  // globals set up and used in each test scenario
  var mock_inventory_service, controller;
  var mapping_controller_scope;
  var timeout, mock_user_service;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, urls, $q, inventory_service, $timeout, user_service) {
      controller = $controller;
      mapping_controller_scope = $rootScope.$new();
      timeout = $timeout;
      mock_user_service = user_service;

      spyOn(mock_user_service, 'set_default_columns')
        .andCallFake(function () {
          return undefined;
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_mapping_controller() {
    var mock_datasets = [{
      name: 'DC 2013 data',
      last_modified: (new Date()).getTime(),
      last_modified_by: 'demo@seed-platform.org',
      number_of_buildings: 89,
      id: 1
    }, {
      name: 'DC 2014 data',
      last_modified: (new Date()).getTime() - 1550 * 60 * 60 * 1000,
      last_modified_by: 'demo2@seed-platform.org',
      number_of_buildings: 70,
      id: 2
    }];
    var fake_import_file_payload = {
      status: 'success',
      import_file: {
        file_name: 'assessor_fun.csv',
        last_modified: (new Date()).getTime(),
        last_modified_by: 'demo@seed-platform.org',
        source_type: 'AssessorRaw',
        dataset: mock_datasets[0],
        id: 1
      }
    };

    var fake_property_columns = [{
      is_extra_data: false,
      display_name: 'PM Property ID',
      name: 'pm_property_id_1',
      data_type: 'string',
      sharedFieldType: 'None',
      table_name: 'PropertyState',
      pinnedLeft: true,
      id: 1,
      column_name: 'pm_property_id'
    }, {
      is_extra_data: false,
      display_name: 'Property Name',
      name: 'property_name_2',
      data_type: 'string',
      sharedFieldType: 'None',
      table_name: 'PropertyState',
      id: 2,
      column_name: 'property_name'
    }, {
      is_extra_data: false,
      display_name: 'Property Notes',
      name: 'property_notes_3',
      data_type: 'string',
      sharedFieldType: 'None',
      table_name: 'PropertyState',
      id: 3,
      column_name: 'property_notes'
    }];

    var fake_taxlot_columns = [{
      is_extra_data: false,
      display_name: 'Jurisdiction Tax Lot ID',
      name: 'jurisdiction_tax_lot_id_4',
      data_type: 'string',
      sharedFieldType: 'None',
      table_name: 'TaxLotState',
      pinnedLeft: true,
      id: 4,
      column_name: 'jurisdiction_tax_lot_id'
    }];

    var mock_mapping_suggestions_payload = {
      status: 'success',
      suggested_column_mappings: {
        'property id': ['PropertyState', 'pm_property_id', 90],
        property_name: ['PropertyState', 'property_name', 100],
        property_notes: ['PropertyState', 'property_notes', 100],
        'lot number': ['TaxLotState', 'jurisdiction_tax_lot_id', 100],
        'lot size': ['PropertyState', 'lot size', 100]
      },
      property_columns: fake_property_columns,
      taxlot_columns: fake_taxlot_columns
    };

    var mock_raw_column_names = [
      'property id',
      'property_name',
      'property_notes',
      'lot number',
      'lot size'
    ];

    var mock_first_five_rows = [];
    for (var i = 0; i < 4; i++) {
      mock_first_five_rows.push({
        'property id': i,
        property_name: 'Property ' + i,
        property_notes: 'Nup.',
        'lot number': i * 2,
        'lot size': 454 * i
      });
    }

    mock_first_five_rows.push({
      'property id': '121L',
      property_name: 'Inconsistent Property',
      property_notes: 'N/A',
      'lot number': 'N/A',
      'lot size': 45
    });

    var mock_cycles = {
      cycles: []
    };

    mock_cycles.cycles.push({
      id: 2015,
      name: 'my fake cycle'
    });

    var raw_columns_payload = {
      status: 'success',
      raw_columns: mock_raw_column_names
    };
    var first_five_rows_payload = {
      status: 'success',
      first_five_rows: mock_first_five_rows
    };
    controller('mapping_controller', {
      $scope: mapping_controller_scope,
      import_file_payload: fake_import_file_payload,
      suggested_mappings_payload: mock_mapping_suggestions_payload,
      raw_columns_payload: raw_columns_payload,
      first_five_rows_payload: first_five_rows_payload,
      cycles: mock_cycles,
      inventory_service: mock_inventory_service
    });
  }

  /**
   * Test scenarios
   */

  it('should have an import_file_payload', function () {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();

    // assertions
    expect(mapping_controller_scope.import_file.dataset.name).toBe('DC 2013 data');
  });

  it('should show suggested mappings', function () {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();

    // assertions
    var mappings = mapping_controller_scope.mappings;
    var first_column = mappings[0];

    expect(first_column.suggestion).toBe('PM Property ID');
  });

  it('should detect duplicates', function () {
    create_mapping_controller();
    mapping_controller_scope.$digest();
    console.log('mappings', angular.copy(mapping_controller_scope.mappings));

    expect(mapping_controller_scope.mappings[0].is_duplicate).toBe(false);
    expect(mapping_controller_scope.mappings[1].is_duplicate).toBe(false);

    // Set the property_name mapping suggestion to the same as the property_id mapping (mappings[0])
    mapping_controller_scope.mappings[1].suggestion = 'PM Property ID';
    mapping_controller_scope.change(mapping_controller_scope.mappings[1]);

    expect(mapping_controller_scope.mappings[0].is_duplicate).toBe(true);
    expect(mapping_controller_scope.mappings[1].is_duplicate).toBe(true);

    // Correct the duplicate
    mapping_controller_scope.mappings[1].suggestion = 'Property Name';
    mapping_controller_scope.change(mapping_controller_scope.mappings[1]);

    expect(mapping_controller_scope.mappings[0].is_duplicate).toBe(false);
    expect(mapping_controller_scope.mappings[1].is_duplicate).toBe(false);
  });

  // Needs to be an e2e test.
  // it('should get mapped buildings', function() {
  //     // arrange
  //     create_mapping_controller();

  //     // act
  //     mapping_controller_scope.$digest();
  //     mapping_controller_scope.get_mapped_buildings();
  //     mapping_controller_scope.$digest();

  //     // assertions
  //     expect(mapping_controller_scope.search.search_buildings).toHaveBeenCalled();
  //     expect(mock_user_service.set_default_columns).toHaveBeenCalled();
  // });

  it('should enable the "show & review buildings" button if duplicates are not present', function () {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();
    for (var i = mapping_controller_scope.mappings.length - 1; i >= 0; i--) {
      mapping_controller_scope.change(mapping_controller_scope.mappings[i]);
    }
    var duplicates_found = mapping_controller_scope.duplicates_present;

    // assertions
    expect(duplicates_found).toBe(false);
  });

  it('should disable the "show & review buildings" button if duplicates are present', function () {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();
    for (var i = mapping_controller_scope.mappings.length - 1; i >= 0; i--) {
      mapping_controller_scope.mappings[i].suggestion = 'PM Property ID';
      mapping_controller_scope.change(mapping_controller_scope.mappings[i]);
    }
    var duplicates_found = mapping_controller_scope.duplicates_present;

    // assertions
    expect(duplicates_found).toBe(true);
  });

  it('should get mappings in an API friendly way', function () {
    create_mapping_controller();
    mapping_controller_scope.$digest();
    var mappings = mapping_controller_scope.get_mappings();
    expect(mappings.length).toBe(5);
    expect(mappings[0]).toEqual({
      from_field: 'property id',
      from_units: null,
      to_field: 'pm_property_id',
      to_field_display_name: 'PM Property ID',
      to_table_name: 'PropertyState'
    });
    // everything in between is empty since we we're using only
    // suggested mappings.
    expect(mappings[3]).toEqual({
      from_field: 'lot number',
      from_units: null,
      to_field: 'jurisdiction_tax_lot_id',
      to_field_display_name: 'Jurisdiction Tax Lot ID',
      to_table_name: 'TaxLotState'
    });
  });

  // Needs to be e2e test now.
  // it('should show the "STEP 2" tab when reviewing mappings', function() {
  //     // arrange
  //     create_mapping_controller();
  //     mapping_controller_scope.$digest();

  //     // act
  //     var mappings = mapping_controller_scope.get_mapped_buildings();

  //     // assert
  //     expect(mapping_controller_scope.tabs).toEqual({
  //         one_active: false,
  //         two_active: true,
  //         three_active: false
  //     });
  // });
});
