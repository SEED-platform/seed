/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: mapping_controller', function () {
  // globals set up and used in each test scenario
  var mock_inventory_service, scope, controller, modal_state;
  var mapping_controller, mapping_controller_scope, modalInstance, labels;
  var timeout, mock_user_service;



  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(
    function ($controller, $rootScope, $uibModal, urls, $q, inventory_service, $timeout, user_service) {
      controller = $controller;
      scope = $rootScope;
      mapping_controller_scope = $rootScope.$new();
      modal_state = '';
      timeout = $timeout;
      mock_user_service = user_service;

      spyOn(mock_user_service, 'set_default_columns')
        .andCallFake(function (mapped_columns) {
          return undefined;
        });
    }
  ));

  // this is outside the beforeEach so it can be configured by each unit test
  function create_mapping_controller () {
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

    var mock_be_building_columns = [
      'pm_property_id',
      'property_name',
      'property_notes',
      'tax_lot_id',
      'gross_floor_area',
      'My New non-BEDES field'
    ];

    var fake_all_columns = [{
      title: 'PM Property ID',
      name: 'pm_property_id',
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
      name: 'tax_lot_id',
      'class': 'is_aligned_right',
      title_class: '',
      type: 'link',
      field_type: 'building_information',
      sortable: true,
      checked: false,
      'static': false,
      link: true
    }, {
      title: 'Gross Floor Area',
      name: 'gross_floor_area',
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
      name: 'property_name',
      'class': '',
      title_class: '',
      type: 'string',
      field_type: 'building_information',
      sortable: true,
      checked: false
    }];

    var mock_be_building_types = {
      gross_floor_area: {
        unit_type: 'float',
        schema: 'BEDES'
      }
    };

    var mock_mapping_suggestions_payload = {
      status: 'success',
      suggested_column_mappings: {
        // key(django model attribute): [csv_header1, ... csv_header3]
        'property id': ['', 'pm_property_id', 89],
        'lot number': ['', 'tax_lot_id', 54]
      },
      columns: fake_all_columns,
      column_names: mock_be_building_columns
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
    mapping_controller = controller('mapping_controller', {
      $scope: mapping_controller_scope,
      import_file_payload: fake_import_file_payload,
      suggested_mappings_payload: mock_mapping_suggestions_payload,
      raw_columns_payload: raw_columns_payload,
      property_columns: mock_raw_column_names,
      taxlot_columns: mock_raw_column_names,
      first_five_rows_payload: first_five_rows_payload,
      all_columns: {fields: []},
      inventory_service: mock_inventory_service,
      $timeout: timeout,
      cycles: mock_cycles
    });
  }

  /**
   * Test scenarios
   */

  it('should have a import_file_payload', function () {
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
    var raw_columns = mapping_controller_scope.raw_columns;
    var first_column = raw_columns[0];

    expect(first_column.confidence).toBe(89);
    expect(first_column.suggestion).toBe('Pm Property Id');
  });

  it('should show \'low\', \'med\', \'high\', or \'\' confidence text', function () {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();

    // assertions
    var raw_columns = mapping_controller_scope.raw_columns;
    var first_column = raw_columns[0];
    expect(first_column.confidence_text()).toBe('high');
    first_column.confidence = 70;
    expect(first_column.confidence_text()).toBe('med');
    first_column.confidence = 35;
    expect(first_column.confidence_text()).toBe('low');
    delete(first_column.confidence);
    expect(first_column.confidence_text()).toBe('');
  });

  it('should validate initial data', function () {
    create_mapping_controller();
    // act
    mapping_controller_scope.$digest();
    // assertions
    angular.forEach(mapping_controller_scope.raw_columns, function (rc) {
      if (!_.isEmpty(rc.suggestion) && !_.isUndefined(rc.suggestion)) {
        expect(rc.validity).toBe('valid');
      }
    });
  });

  // it('should invalidate bad suggestions', function() {
  //     // Simulate a change on the tcm, make it fail.
  //     create_mapping_controller();
  //     // act
  //     mapping_controller_scope.$digest();
  //     // assertions
  //     //
  //     // We change the suggested mapping for the "property name" column
  //     // to "gross_floor_area" (which validates as float) to
  //     // purposely cause a failing change.
  //     mapping_controller_scope.raw_columns[0].suggestion = 'gross_floor_area';
  //     mapping_controller_scope.validate_data(mapping_controller_scope.raw_columns[0]);
  //     expect(mapping_controller_scope.raw_columns[0].validity).toBe('invalid');

  // });

  it('should set td_class appropriately', function () {
    var tcm;

    create_mapping_controller();

    mapping_controller_scope.$digest();
    tcm = mapping_controller_scope.raw_columns[0];
    tcm.invalids = [tcm.raw_data[0]];
    tcm.validity = "invalid";
    var good_val = mapping_controller_scope.set_td_class(
      tcm,
      tcm.raw_data[0]
    );

    // Now we're saying the suggestion is to not map.
    // Check that we don't have any class set for this row now.
    mapping_controller_scope.raw_columns[0].suggestion = '';
    mapping_controller_scope.validate_data(mapping_controller_scope.raw_columns[0]);

    tcm = mapping_controller_scope.raw_columns[0];
    tcm.invalids = [tcm.raw_data[4]];
    tcm.validity = "semivalid";
    var blank_val = mapping_controller_scope.set_td_class(
      tcm,
      tcm.raw_data[4]
    );

    expect(blank_val).toBe('');
  });

  it('should test labels', function () {
    var tcm;

    create_mapping_controller();

    mapping_controller_scope.$digest();
    tcm = mapping_controller_scope.raw_columns[0];
    expect(tcm.label_status()).toBe('success');

    tcm.mapped_row = false;
    expect(tcm.label_status()).toBe('default');

    tcm.mapped_row = true;
    tcm.validity = "invalid";
    expect(tcm.label_status()).toBe('danger');

    tcm.mapped_row = true;
    tcm.validity = "somethingElse";
    expect(tcm.label_status()).toBe('warning');
  });


  it('should detect duplicates of mapped rows', function () {
    create_mapping_controller();
    mapping_controller_scope.$digest();

    // raw_columns[0] and raw_columns[3] should be the only mapped rows

    expect(mapping_controller_scope.raw_columns[3].is_duplicate).toBe(false);

    // Set the property_name tcm's suggestion to the same as
    // the property_id tcm (raw_columns[0])
    mapping_controller_scope.raw_columns[3].suggestion = 'Pm Property Id';
    mapping_controller_scope.updateColDuplicateStatus();
    mapping_controller_scope.$digest();

    expect(mapping_controller_scope.raw_columns[3].is_duplicate).toBe(true);

    // Since we mark both duplicates as duplicates, the other
    // TCM that has the 'pm_property_id' suggestion should also get
    // 'danger' as its duplicate class.
    expect(mapping_controller_scope.raw_columns[0].is_duplicate).toBe(true);

    // Shows that mapped_row is the sole determinant of
    // column ignoring
    mapping_controller_scope.raw_columns[0].mapped_row = false;
    mapping_controller_scope.updateColDuplicateStatus();
    mapping_controller_scope.$digest();

    expect(mapping_controller_scope.raw_columns[0].is_duplicate).toBe(false);

  });

  it('should ignore duplicates of unmapped rows', function () {
    create_mapping_controller();
    mapping_controller_scope.$digest();

    // raw_columns[0] and raw_columns[3] should be the only mapped rows

    expect(mapping_controller_scope.raw_columns[1].is_duplicate).toBe(false);

    // Set the property_name tcm's suggestion to the same as
    // the property_id tcm (raw_columns[0])
    mapping_controller_scope.raw_columns[1].suggestion = 'Pm Property Id';

    expect(mapping_controller_scope.raw_columns[0].is_duplicate).toBe(false);
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

  it('should enable the \'show & review buildings\' button if duplicates are not present', function () {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();
    for (var i = mapping_controller_scope.raw_columns.length - 1; i >= 0; i--) {
      mapping_controller_scope.change(mapping_controller_scope.raw_columns[i]);
    }
    var duplicates_found = mapping_controller_scope.duplicates_present();

    // assertions
    expect(duplicates_found).toBe(false);
  });

  it('should disable the \'show & review buildings\' button if duplicates are present', function () {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();
    for (var i = mapping_controller_scope.raw_columns.length - 1; i >= 0; i--) {
      mapping_controller_scope.raw_columns[i].suggestion = 'pm_property_id';
      mapping_controller_scope.change(mapping_controller_scope.raw_columns[i]);
    }
    var duplicates_found = mapping_controller_scope.duplicates_present();

    // assertions
    expect(duplicates_found).toBe(true);
  });

  it('should get mappings in an API friendly way', function () {
    create_mapping_controller();
    mapping_controller_scope.$digest();
    var mappings = mapping_controller_scope.get_mappings();
    expect(mappings.length).toBe(5);
    expect(mappings[0]).toEqual({ from_field: 'property id', to_field: 'Pm Property Id', to_table_name: '' });
    // everything in between is empty since we we're using only
    // suggested mappings.
    expect(mappings[3]).toEqual({ from_field: 'lot number', to_field: 'Tax Lot Id', to_table_name: '' });
  });

  // Needs to be e2e test now.
  // it('should show the \'STEP 2\' tab when reviewing mappings', function() {
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
