/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// Latitude and longitude must keep full precision on the cross-cycles pages instead of being
// rounded to the organization's display_decimal_places setting (GitHub issue #4132).
describe('cross-cycles latitude/longitude display', () => {
  const organization = {
    id: 1, display_decimal_places: 2, property_display_field: 'address_line_1', taxlot_display_field: 'address_line_1'
  };
  const spinner_utility = { show: () => {}, hide: () => {} };
  const columns = [
    {
      id: 1, column_name: 'latitude', data_type: 'number', table_name: 'PropertyState', is_extra_data: false
    },
    {
      id: 2, column_name: 'longitude', data_type: 'number', table_name: 'PropertyState', is_extra_data: false
    },
    {
      id: 3, column_name: 'site_eui', data_type: 'eui', table_name: 'PropertyState', is_extra_data: false
    }
  ];

  let $controller;
  let $rootScope;

  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject((_$controller_, _$rootScope_) => {
      $controller = _$controller_;
      $rootScope = _$rootScope_;
    });
  });

  it('inventory_cycles_controller does not round lat/long to the org decimal setting', () => {
    const scope = $rootScope.$new();
    $controller('inventory_cycles_controller', {
      $scope: scope,
      $stateParams: { inventory_type: 'properties' },
      inventory: {},
      cycles: { cycles: [] },
      organization_payload: { organization },
      profiles: [],
      current_profile: undefined,
      all_columns: _.cloneDeep(columns),
      matching_criteria_columns: { PropertyState: [], TaxLotState: [] },
      spinner_utility
    });

    expect(_.find(scope.columns, { column_name: 'latitude' }).cellFilter).toBe('floatingPoint');
    expect(_.find(scope.columns, { column_name: 'longitude' }).cellFilter).toBe('floatingPoint');
    expect(_.find(scope.columns, { column_name: 'site_eui' }).cellFilter).toBe('number: 2');
  });

  it('inventory_detail_cycles_controller does not round lat/long to the org decimal setting', () => {
    const scope = $rootScope.$new();
    $controller('inventory_detail_cycles_controller', {
      $scope: scope,
      $stateParams: { inventory_type: 'properties', view_id: 1 },
      cycles: { cycles: [] },
      inventory_payload: { data: [{ view_id: 1, cycle_id: 1, extra_data: {} }] },
      columns: _.cloneDeep(columns),
      profiles: [],
      current_profile: undefined,
      organization_payload: { organization },
      spinner_utility
    });

    expect(scope.displayValue(columns[0], 39.7392358)).toBe(39.7392358);
    expect(scope.displayValue(columns[1], -104.990251)).toBe(-104.990251);
    expect(scope.displayValue(columns[2], 12.3456)).toBe('12.35');
  });
});
