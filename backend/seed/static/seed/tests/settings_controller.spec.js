/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: organization_settings_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let ctrl_scope;
  let mock_organization_service;
  let mock_meters_service;

  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
      _$httpBackend_.whenGET('/api/v3/audit_template/report_types/').respond(200, { status: 'success', data: [] });
    });
    inject(($controller, $rootScope, $uibModal, $q, organization_service, meters_service) => {
      controller = $controller;
      ctrl_scope = $rootScope.$new();

      mock_organization_service = organization_service;
      mock_meters_service = meters_service;

      spyOn(mock_organization_service, 'save_org_settings').and.callFake(() => $q.resolve({ status: 'success' }));

      spyOn(mock_meters_service, 'valid_energy_types_units').and.callFake(() => $q.resolve({ status: 'success' }));
    });
  });

  const default_property_columns = [
    {
      id: 500,
      name: 'test',
      organization_id: 4,
      table_name: 'TaxLotState',
      column_name: 'test'
    },
    {
      id: 501,
      name: 'test',
      organization_id: 4,
      table_name: 'PropertyState',
      column_name: 'test'
    }
  ];

  // this is outside the beforeEach so it can be configured by each unit test
  function create_settings_controller(property_columns = default_property_columns) {
    controller('organization_settings_controller', {
      $scope: ctrl_scope,
      all_columns: {
        fields: [
          { checked: false, title: 'PM Property ID', sort_column: 'pm_property_id' },
          { checked: false, title: 'G', sort_column: 'g' },
          { checked: false, title: 'Gross Floor Area', sort_column: 'gross_floor_area' }
        ]
      },
      organization_payload: {
        organization: {
          name: 'my org', id: 4, default_reports_x_axis_options: [], default_reports_y_axis_options: [], bb_salesforce_enabled: false
        }
      },
      query_threshold_payload: {
        query_threshold: 10
      },
      shared_fields_payload: {
        shared_fields: [
          {
            title: 'PM Property ID',
            sort_column: 'pm_property_id'
          }
        ],
        public_fields: [
          {
            title: 'Gross Floor Area',
            sort_column: 'gross_floor_area'
          }
        ]
      },
      auth_payload: {
        auth: {
          is_owner: true,
          is_parent_org_owner: false
        }
      },
      cycles_payload: [
        {
          status: 'success',
          cycles: [
            {
              id: 1,
              name: 'Cycle 1',
              organization_id: 4,
              start_date: '2023-01-01',
              end_date: '2023-12-31',
              default: true
            }
          ]
        }
      ],
      labels_payload: [
        {
          id: 47,
          name: 'Add to Salesforce',
          organization_id: 4
        }
      ],
      salesforce_mappings_payload: [],
      salesforce_configs_payload: [
        {
          id: 1,
          organization_id: 4,
          unique_benchmark_id_fieldname: 'Salesforce_Benchmark_ID__c'
        }
      ],
      bb_salesforce_configs_payload: {},
      audit_template_configs_payload: [],
      property_column_names: { column_name: 'test', display_name: 'test' },
      taxlot_column_names: { column_name: 'test', display_name: 'test' },
      property_columns,
      facilities_plans: []
    });
  }

  /**
   * Test scenarios
   */

  it('should accepts its payload', () => {
    // arrange
    create_settings_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.save_settings();
    ctrl_scope.$digest();

    // assertions
    expect(ctrl_scope.org).toEqual({
      bb_salesforce_enabled: false,
      name: 'my org',
      id: 4,
      default_reports_x_axis_options: [],
      default_reports_y_axis_options: []
      // query_threshold: 10
    });
    expect(mock_organization_service.save_org_settings).toHaveBeenCalledWith(ctrl_scope.org);
    expect(mock_meters_service.valid_energy_types_units).toHaveBeenCalled();
    expect(ctrl_scope.settings_updated).toEqual(true);
    // expect(ctrl_scope.fields[0].checked).toEqual(true);
    // expect(ctrl_scope.fields[1].checked).toEqual(false);
    // expect(ctrl_scope.fields[0].title).toEqual('PM Property ID');
  });

  it('should sort the report axis column options by display name', () => {
    // arrange: server order is non-extra-data (including derived) first, then extra data
    create_settings_controller([
      {
        id: 1, displayName: 'Year Built', data_type: 'integer', is_extra_data: false
      },
      {
        id: 2, displayName: 'TotalSiteEnergy', data_type: 'string', derived_column: 3, is_extra_data: false
      },
      {
        id: 3, displayName: 'Address Line 1', data_type: 'string', is_extra_data: false
      },
      {
        id: 4, displayName: 'Building Count', data_type: 'integer', is_extra_data: true
      },
      {
        id: 5, displayName: 'area', data_type: 'area', is_extra_data: true
      }
    ]);

    // act
    ctrl_scope.$digest();

    // assertions
    expect(ctrl_scope.available_x_columns().map((c) => c.displayName)).toEqual(['Address Line 1', 'area', 'Building Count', 'TotalSiteEnergy', 'Year Built']);
    expect(ctrl_scope.available_y_columns().map((c) => c.displayName)).toEqual(['area', 'Building Count', 'TotalSiteEnergy', 'Year Built']);
    // the original column order is left unchanged
    expect(ctrl_scope.columns.map((c) => c.id)).toEqual([1, 2, 3, 4, 5]);
  });
  // it('should select all', function() {
  //     // arrange
  //     create_settings_controller();

  //     // act
  //     ctrl_scope.$digest();
  //     ctrl_scope.controls.select_all = true;
  //     ctrl_scope.select_all_clicked();
  //     ctrl_scope.$digest();

  //     // assertions
  //     expect(ctrl_scope.infinite_fields[0].checked).toEqual(true);
  // });
});
