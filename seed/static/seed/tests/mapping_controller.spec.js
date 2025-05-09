/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: mapping_controller', () => {
  // globals set up and used in each test scenario
  let mock_inventory_service;
  let controller;
  let mapping_controller_scope;
  let mock_geocode_service;
  let mock_organization_service;

  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $uibModal, urls, $q, inventory_service, geocode_service, organization_service) => {
      controller = $controller;
      mapping_controller_scope = $rootScope.$new();
      mock_geocode_service = geocode_service;
      mock_organization_service = organization_service;

      spyOn(mock_geocode_service, 'check_org_has_api_key').andCallFake(() => $q.resolve({ status: 'success' }));

      spyOn(mock_geocode_service, 'check_org_has_geocoding_enabled').andCallFake(() => $q.resolve(true));

      spyOn(mock_organization_service, 'geocoding_columns').andCallFake(() => $q.resolve({ status: 'success' }));
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_mapping_controller() {
    const mock_datasets = [
      {
        name: 'DC 2013 data',
        last_modified: new Date().getTime(),
        last_modified_by: 'demo@seed-platform.org',
        number_of_buildings: 89,
        id: 1
      },
      {
        name: 'DC 2014 data',
        last_modified: new Date().getTime() - 1550 * 60 * 60 * 1000,
        last_modified_by: 'demo2@seed-platform.org',
        number_of_buildings: 70,
        id: 2
      }
    ];
    const fake_import_file_payload = {
      status: 'success',
      import_file: {
        file_name: 'assessor_fun.csv',
        last_modified: new Date().getTime(),
        last_modified_by: 'demo@seed-platform.org',
        source_type: 'AssessorRaw',
        dataset: mock_datasets[0],
        id: 1,
        cycle: 2015
      }
    };

    const fake_property_columns = [
      {
        column_name: 'pm_property_id',
        data_type: 'string',
        display_name: 'PM Property ID',
        column_description: 'PM Property ID',
        id: 1,
        is_extra_data: false,
        name: 'pm_property_id_1',
        pinnedLeft: true,
        sharedFieldType: 'None',
        table_name: 'PropertyState'
      },
      {
        column_name: 'property_name',
        data_type: 'string',
        display_name: 'Property Name',
        column_description: 'Property Name',
        id: 2,
        is_extra_data: false,
        name: 'property_name_2',
        sharedFieldType: 'None',
        table_name: 'PropertyState'
      },
      {
        column_name: 'property_notes',
        data_type: 'string',
        display_name: 'Property Notes',
        column_description: 'Property Notes',
        id: 3,
        is_extra_data: false,
        name: 'property_notes_3',
        sharedFieldType: 'None',
        table_name: 'PropertyState'
      },
      {
        column_name: 'address_line_1',
        data_type: 'string',
        display_name: 'Address Line 1',
        column_description: 'Address Line 1',
        id: 4,
        is_extra_data: false,
        name: 'address_line_1_4',
        sharedFieldType: 'None',
        table_name: 'PropertyState'
      },
      {
        column_name: 'custom_id_1',
        data_type: 'string',
        display_name: 'Custom ID 1',
        column_description: 'Custom ID 1',
        id: 5,
        is_extra_data: false,
        name: 'custom_id_1_5',
        sharedFieldType: 'None',
        table_name: 'PropertyState'
      },
      {
        column_name: 'ubid',
        data_type: 'string',
        display_name: 'UBID',
        column_description: 'UBID',
        id: 6,
        is_extra_data: false,
        name: 'ubid_6',
        sharedFieldType: 'None',
        table_name: 'PropertyState'
      }
    ];

    const fake_taxlot_columns = [
      {
        column_name: 'address_line_1',
        data_type: 'string',
        display_name: 'Address Line 1',
        id: 7,
        is_extra_data: false,
        name: 'address_line_1_7',
        sharedFieldType: 'None',
        table_name: 'TaxLotState'
      },
      {
        column_name: 'custom_id_1',
        data_type: 'string',
        display_name: 'Custom ID 1',
        column_description: 'Custom ID 1',
        id: 8,
        is_extra_data: false,
        name: 'custom_id_1_8',
        sharedFieldType: 'None',
        table_name: 'TaxLotState'
      },
      {
        column_name: 'jurisdiction_tax_lot_id',
        data_type: 'string',
        display_name: 'Jurisdiction Tax Lot ID',
        column_description: 'Jurisdiction Tax Lot ID',
        id: 9,
        is_extra_data: false,
        name: 'jurisdiction_tax_lot_id_9',
        sharedFieldType: 'None',
        table_name: 'TaxLotState'
      },
      {
        column_name: 'ubid',
        data_type: 'string',
        display_name: 'UBID',
        column_description: 'UBID',
        id: 10,
        is_extra_data: false,
        name: 'ubid_10',
        sharedFieldType: 'None',
        table_name: 'TaxLotState'
      }
    ];

    const mock_mapping_suggestions_payload = {
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

    const mock_matching_criteria_columns_payload = {
      PropertyState: ['address_line_1', 'custom_id_1', 'pm_property_id', 'ubid'],
      TaxLotState: ['address_line_1', 'custom_id_1', 'jurisdiction_tax_lot_id', 'ubid']
    };

    const mock_raw_column_names = ['property id', 'property_name', 'property_notes', 'lot number', 'lot size'];

    const mock_first_five_rows = [];
    for (let i = 0; i < 4; i++) {
      mock_first_five_rows.push({
        'property id': i,
        property_name: `Property ${i}`,
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

    const mock_cycles = {
      cycles: []
    };

    mock_cycles.cycles.push({
      id: 2015,
      name: 'my fake cycle'
    });

    const raw_columns_payload = {
      status: 'success',
      raw_columns: mock_raw_column_names
    };
    const first_five_rows_payload = {
      status: 'success',
      first_five_rows: mock_first_five_rows
    };
    const fake_derived_columns_payload = {
      derived_columns: []
    };

    const fake_organization_payload = {
      status: 'success',
      organization: {
        display_decimal_places: 2,
        id: 1,
        access_level_names: []
      }
    };

    controller('mapping_controller', {
      $scope: mapping_controller_scope,
      import_file_payload: fake_import_file_payload,
      suggested_mappings_payload: mock_mapping_suggestions_payload,
      raw_columns_payload,
      first_five_rows_payload,
      matching_criteria_columns_payload: mock_matching_criteria_columns_payload,
      column_mapping_profiles_payload: [],
      cycles: mock_cycles,
      inventory_service: mock_inventory_service,
      organization_payload: fake_organization_payload,
      derived_columns_payload: fake_derived_columns_payload
    });
  }

  /**
   * Test scenarios
   */

  it('should have an import_file_payload', () => {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();

    // assertions
    expect(mapping_controller_scope.import_file.dataset.name).toBe('DC 2013 data');
    expect(mapping_controller_scope.import_file.cycle).toEqual(2015);
    expect(mock_geocode_service.check_org_has_api_key).toHaveBeenCalled();
    expect(mock_organization_service.geocoding_columns).toHaveBeenCalled();
  });

  it('should detect duplicates', () => {
    create_mapping_controller();
    mapping_controller_scope.$digest();
    mapping_controller_scope.mappings[0].suggestion = 'PM Property ID';
    mapping_controller_scope.mappings[1].suggestion = 'Property Name';

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

    expect(mock_geocode_service.check_org_has_api_key).toHaveBeenCalled();
    expect(mock_organization_service.geocoding_columns).toHaveBeenCalled();
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
  // });

  it('should enable the "show & review buildings" button if duplicates are not present', () => {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();
    for (let i = mapping_controller_scope.mappings.length - 1; i >= 0; i--) {
      mapping_controller_scope.change(mapping_controller_scope.mappings[i]);
    }
    const duplicates_found = mapping_controller_scope.duplicates_present;

    // assertions
    expect(duplicates_found).toBe(false);
    expect(mock_geocode_service.check_org_has_api_key).toHaveBeenCalled();
    expect(mock_organization_service.geocoding_columns).toHaveBeenCalled();
  });

  it('should disable the "show & review buildings" button if duplicates are present', () => {
    // arrange
    create_mapping_controller();

    // act
    mapping_controller_scope.$digest();
    for (let i = mapping_controller_scope.mappings.length - 1; i >= 0; i--) {
      mapping_controller_scope.mappings[i].suggestion = 'PM Property ID';
      mapping_controller_scope.change(mapping_controller_scope.mappings[i]);
    }
    const duplicates_found = mapping_controller_scope.duplicates_present;

    // assertions
    expect(duplicates_found).toBe(true);
    expect(mock_geocode_service.check_org_has_api_key).toHaveBeenCalled();
    expect(mock_organization_service.geocoding_columns).toHaveBeenCalled();
  });
});
