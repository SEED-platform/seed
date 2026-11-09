/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
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

      spyOn(mock_geocode_service, 'check_org_has_api_key').and.callFake(() => $q.resolve({ status: 'success' }));

      spyOn(mock_geocode_service, 'check_org_has_geocoding_enabled').and.callFake(() => $q.resolve(true));

      spyOn(mock_organization_service, 'geocoding_columns').and.callFake(() => $q.resolve({ status: 'success' }));
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_mapping_controller(column_mapping_profiles_payload = []) {
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
      column_mapping_profiles_payload,
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
  //     mapping_controller_scope.start_mapped_buildings();
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
    const duplicates_found = mapping_controller_scope.duplicate_headers_present || mapping_controller_scope.duplicate_suggestions_present;

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
    const duplicates_found = mapping_controller_scope.duplicate_headers_present || mapping_controller_scope.duplicate_suggestions_present;

    // assertions
    expect(duplicates_found).toBe(true);
    expect(mock_geocode_service.check_org_has_api_key).toHaveBeenCalled();
    expect(mock_organization_service.geocoding_columns).toHaveBeenCalled();
  });

  it('should list canonical columns before extra data columns in the 20-item typeahead (#4175)', () => {
    // arrange: 25 extra data columns that sort alphabetically before the canonical column
    const columns = [];
    for (let i = 0; i < 25; i++) {
      columns.push({ display_name: `${String.fromCharCode(65 + (i % 6))}${i} - Gross Floor Area (ft2)`, is_extra_data: true });
    }
    columns.push({ display_name: 'Gross Floor Area', is_extra_data: false });
    columns.push({ display_name: 'Zz - Gross Floor Area (ft2)', is_extra_data: true });
    mapping_controller_scope.mappable_property_columns = columns;
    mapping_controller_scope.view_value = 'Gross Floor Area';

    // act: same filter chain as the mapping.html typeahead
    const matches = mapping_controller_scope.$eval("mappable_property_columns | filter:{display_name:view_value} | orderBy:'is_extra_data' | limitTo:20");

    // assertions
    expect(matches.length).toBe(20);
    expect(matches[0].display_name).toBe('Gross Floor Area');
    // extra data columns keep their original (alphabetical) order
    expect(matches.slice(1).map((c) => c.display_name)).toEqual(columns.slice(0, 19).map((c) => c.display_name));
  });

  it('should warn when a Multiple Cycle Upload does not map year_ending (#4052)', () => {
    create_mapping_controller();
    mapping_controller_scope.$digest();
    const col = mapping_controller_scope.mappings[0];
    col.suggestion_table_name = 'PropertyState';
    col.suggestion_column_name = 'pm_property_id';
    col.is_omitted = false;

    // not a multiple cycle upload: no warning
    mapping_controller_scope.import_file.multiple_cycle_upload = false;
    expect(mapping_controller_scope.year_ending_unmapped()).toBe(false);

    // multiple cycle upload without a year_ending mapping: warn
    mapping_controller_scope.import_file.multiple_cycle_upload = true;
    expect(mapping_controller_scope.year_ending_unmapped()).toBe(true);

    // year_ending mapped on a tax lot or omitted doesn't count
    col.suggestion_column_name = 'year_ending';
    col.suggestion_table_name = 'TaxLotState';
    expect(mapping_controller_scope.year_ending_unmapped()).toBe(true);
    col.suggestion_table_name = 'PropertyState';
    col.is_omitted = true;
    expect(mapping_controller_scope.year_ending_unmapped()).toBe(true);

    // year_ending mapped on a property: no warning
    col.is_omitted = false;
    expect(mapping_controller_scope.year_ending_unmapped()).toBe(false);
  });

  describe('renaming and deleting column mapping profiles (#4974)', () => {
    let mock_uib_modal;
    let modal_result;

    const fake_profiles = () => [
      {
        id: 11, name: 'Profile A', mappings: [], profile_type: 'Normal'
      },
      {
        id: 12, name: 'Profile B', mappings: [], profile_type: 'Normal'
      },
      {
        id: 13, name: 'BuildingSync Default', mappings: [], profile_type: 'BuildingSync Default'
      }
    ];

    beforeEach(inject(($uibModal, $q) => {
      mock_uib_modal = $uibModal;
      spyOn(mock_uib_modal, 'open').and.callFake(() => ({ result: $q.resolve(modal_result) }));
    }));

    it('should only allow saved, non-BuildingSync Default profiles to be renamed or deleted', () => {
      create_mapping_controller(fake_profiles());
      const scope = mapping_controller_scope;

      expect(scope.selected_profile_editable()).toBe(false);
      scope.dropdown_selected_profile = scope.profiles[1];
      expect(scope.selected_profile_editable()).toBe(true);
      scope.dropdown_selected_profile = scope.profiles[3];
      expect(scope.selected_profile_editable()).toBe(false);
    });

    it('should rename the profile selected in the dropdown', () => {
      create_mapping_controller(fake_profiles());
      const scope = mapping_controller_scope;
      scope.dropdown_selected_profile = scope.profiles[2];
      modal_result = 'Profile B renamed';

      scope.rename_profile();
      scope.$digest();

      const modal_resolve = mock_uib_modal.open.calls.mostRecent().args[0].resolve;
      expect(modal_resolve.action()).toBe('rename');
      expect(modal_resolve.data().id).toBe(12);
      expect(modal_resolve.org_id()).toBe(1);
      expect(scope.profiles.map((p) => p.name)).toEqual(['<None selected>', 'Profile A', 'Profile B renamed', 'BuildingSync Default']);
    });

    it('should delete the selected profile and keep the applied profile', () => {
      create_mapping_controller(fake_profiles());
      const scope = mapping_controller_scope;
      scope.current_profile = scope.profiles[1];
      scope.dropdown_selected_profile = scope.profiles[2];
      scope.profile_change_possible = true;
      modal_result = undefined;

      scope.remove_profile();
      scope.$digest();

      expect(mock_uib_modal.open.calls.mostRecent().args[0].resolve.action()).toBe('remove');
      expect(scope.profiles.map((p) => p.id)).toEqual([0, 11, 13]);
      expect(scope.current_profile.id).toBe(11);
      expect(scope.dropdown_selected_profile.id).toBe(11);
      expect(scope.profile_change_possible).toBe(false);
      // the applied profile still holds the mappings, so they aren't unsaved
      expect(scope.mappings_change_possible).toBeFalsy();
    });

    it('should reset the applied profile when it is deleted', () => {
      create_mapping_controller(fake_profiles());
      const scope = mapping_controller_scope;
      scope.current_profile = scope.profiles[1];
      scope.dropdown_selected_profile = scope.profiles[1];
      modal_result = undefined;

      scope.remove_profile();
      scope.$digest();

      expect(scope.profiles.map((p) => p.id)).toEqual([0, 12, 13]);
      expect(scope.current_profile.id).toBe(0);
      expect(scope.dropdown_selected_profile.id).toBe(0);
      // the kept mappings are no longer saved in a profile, so applying another profile must warn first
      expect(scope.mappings_change_possible).toBe(true);
    });
  });
});
