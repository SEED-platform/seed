/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: data_quality_admin_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let data_quality_admin_controller_scope;

  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
      _$httpBackend_.whenGET(/^\/static\/seed\/partials\/modified_modal\.html/).respond(200, {});
    });
    inject(($controller, $rootScope /* , $q */) => {
      controller = $controller;
      data_quality_admin_controller_scope = $rootScope.$new();
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_data_quality_admin_controller() {
    const col_payload = [
      {
        data_type: 'string',
        displayName: 'Address Line 1',
        column_name: 'address_line_1',
        is_extra_data: false,
        name: 'address_line_1',
        related: false,
        table_name: 'PropertyState'
      }
    ];
    const derived_columns_payload = { derived_columns: [] };
    controller('data_quality_admin_controller', {
      $scope: data_quality_admin_controller_scope,
      columns: col_payload,
      used_columns: col_payload,
      derived_columns_payload,
      organization_payload: {},
      data_quality_rules_payload: {},
      auth_payload: {},
      labels_payload: {}
    });
  }

  /**
   * Test scenarios
   */

  it('should have a check dq rule changes', () => {
    // arrange
    create_data_quality_admin_controller();
    const ruleGroups = {
      properties: {
        address_line_1: [
          {
            autofocus: true,
            data_type: 'date',
            enabled: true,
            field: 'address_line_1',
            label: 1234,
            max: null,
            min: null,
            not_null: true,
            required: false,
            rule_type: 1,
            severity: 'error',
            text_match: null,
            units: ''
          },
          {
            autofocus: true,
            data_type: 'number',
            enabled: true,
            field: 'address_line_1',
            label: null,
            max: null,
            min: null,
            not_null: true,
            required: false,
            rule_type: 1,
            severity: 'error',
            text_match: null,
            units: ''
          }
        ]
      }
    };
    data_quality_admin_controller_scope.ruleGroups = ruleGroups;
    data_quality_admin_controller_scope.rule_type = 'properties';
    // act
    data_quality_admin_controller_scope.change_field(ruleGroups.properties.address_line_1[0], 'address_line_1', 0);
    data_quality_admin_controller_scope.change_data_type(ruleGroups.properties.address_line_1[0], 'string');
    data_quality_admin_controller_scope.remove_label(ruleGroups.properties.address_line_1[0]);
    data_quality_admin_controller_scope.selectAll();

    data_quality_admin_controller_scope.$digest();

    // assertions
    expect(data_quality_admin_controller_scope.ruleGroups.properties.address_line_1[0].label).toEqual(null);
    expect(data_quality_admin_controller_scope.ruleGroups.properties.address_line_1[0].data_type).toEqual('number');
    expect(data_quality_admin_controller_scope.ruleGroups.properties.address_line_1[0].enabled).toEqual(false);
  });
});
