/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// Creating or editing a derived column that references another derived column must not fail
// silently with a TypeError in the circular-definition check (GitHub issue #4429).
describe('controller: derived_columns_editor_controller', () => {
  let $controller;
  let $rootScope;
  let $q;
  let derived_columns_service;

  // dc1 = $param_a / 100 where param_a is the column of dc2, and dc2 = $param_a where param_a is the column of dc1
  const derived_columns = [
    {
      id: 1, name: 'dc1', expression: '$param_a / 100', inventory_type: 'Property', parameters: [{ parameter_name: 'param_a', source_column: 102 }]
    },
    {
      id: 2, name: 'dc2', expression: '$param_a', inventory_type: 'Property', parameters: [{ parameter_name: 'param_a', source_column: 101 }]
    },
    {
      id: 3, name: 'dc3', expression: '$param_a', inventory_type: 'Tax Lot', parameters: [{ parameter_name: 'param_a', source_column: 202 }]
    },
    {
      id: 4, name: 'dc4', expression: '$param_a', inventory_type: 'Tax Lot', parameters: [{ parameter_name: 'param_a', source_column: 201 }]
    }
  ];
  const property_columns = [
    {
      id: 100, column_name: 'gross_floor_area', displayName: 'Gross Floor Area', derived_column: null, related: false
    },
    {
      id: 101, column_name: 'dc1', displayName: 'dc1', derived_column: 1, related: false
    },
    {
      id: 102, column_name: 'dc2', displayName: 'dc2', derived_column: 2, related: false
    }
  ];
  const taxlot_columns = [
    {
      id: 200, column_name: 'lot_area', displayName: 'Lot Area', derived_column: null, related: false
    },
    {
      id: 201, column_name: 'dc3', displayName: 'dc3', derived_column: 3, related: false
    },
    {
      id: 202, column_name: 'dc4', displayName: 'dc4', derived_column: 4, related: false
    }
  ];

  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject((_$controller_, _$rootScope_, _$q_) => {
      $controller = _$controller_;
      $rootScope = _$rootScope_;
      $q = _$q_;
    });
    derived_columns_service = {
      create_derived_column: jasmine.createSpy('create_derived_column').and.callFake((org_id, data) => $q.resolve({ derived_column: { name: data.name } })),
      update_derived_column: jasmine.createSpy('update_derived_column').and.callFake((org_id, id, data) => $q.resolve({ derived_column: { name: data.name } }))
    };
  });

  const create_controller = (inventory_type, derived_column) => {
    const scope = $rootScope.$new();
    $controller('derived_columns_editor_controller', {
      $scope: scope,
      $state: { current: {}, go: jasmine.createSpy('go') },
      $stateParams: { inventory_type },
      derived_columns_service,
      Notification: { success: () => {} },
      modified_service: { setModified: () => {}, resetModified: () => {} },
      simple_modal_service: { showModal: () => $q.resolve() },
      spinner_utility: { show: () => {}, hide: () => {} },
      auth_payload: { auth: {} },
      organization_payload: { organization: { id: 1 } },
      derived_column_payload: { derived_column: derived_column ? _.cloneDeep(derived_column) : undefined },
      derived_columns_payload: { derived_columns: _.cloneDeep(derived_columns) },
      property_columns_payload: _.cloneDeep(property_columns),
      taxlot_columns_payload: _.cloneDeep(taxlot_columns)
    });
    return scope;
  };

  it('creates a new property derived column that references another derived column', () => {
    const scope = create_controller('properties');
    scope.derived_column.name = 'new derived column';
    scope.parameters[0].source_column = _.find(scope.property_columns, { id: 101 });

    expect(() => scope.create_or_update_derived_column()).not.toThrow();
    expect(scope.parameters[0].errors.circular_source_column).toBe(false);
    expect(derived_columns_service.create_derived_column).toHaveBeenCalledWith(1, {
      name: 'new derived column',
      expression: '$param_a / 100',
      inventory_type: 'Property',
      parameters: [{ parameter_name: 'param_a', source_column: 101 }]
    });
  });

  it('creates a new tax lot derived column that references another derived column', () => {
    const scope = create_controller('taxlots');
    scope.derived_column.name = 'new derived column';
    scope.parameters[0].source_column = _.find(scope.taxlot_columns, { id: 201 });

    expect(() => scope.create_or_update_derived_column()).not.toThrow();
    expect(derived_columns_service.create_derived_column).toHaveBeenCalled();
  });

  it('shows an invalid source column error instead of throwing when a parameter has no source column', () => {
    const scope = create_controller('properties');
    scope.derived_column.name = 'new derived column';

    expect(() => scope.create_or_update_derived_column()).not.toThrow();
    expect(scope.parameters[0].errors.invalid_source_column).toBe(true);
    expect(derived_columns_service.create_derived_column).not.toHaveBeenCalled();
  });

  it('flags a circular property definition when editing', () => {
    const scope = create_controller('properties', derived_columns[0]);
    scope.parameters[0].source_column = _.find(scope.property_columns, { id: 102 });

    expect(() => scope.create_or_update_derived_column()).not.toThrow();
    expect(scope.parameters[0].errors.circular_source_column).toBe(true);
    expect(derived_columns_service.update_derived_column).not.toHaveBeenCalled();
  });

  it('flags a circular tax lot definition when editing', () => {
    const scope = create_controller('taxlots', derived_columns[2]);
    scope.parameters[0].source_column = _.find(scope.taxlot_columns, { id: 202 });

    expect(() => scope.create_or_update_derived_column()).not.toThrow();
    expect(scope.parameters[0].errors.circular_source_column).toBe(true);
    expect(derived_columns_service.update_derived_column).not.toHaveBeenCalled();
  });

  it('updates an existing derived column with a regular source column', () => {
    const scope = create_controller('properties', derived_columns[1]);
    scope.parameters[0].source_column = _.find(scope.property_columns, { id: 100 });

    expect(() => scope.create_or_update_derived_column()).not.toThrow();
    expect(scope.parameters[0].errors.circular_source_column).toBe(false);
    expect(derived_columns_service.update_derived_column).toHaveBeenCalled();
  });
});
