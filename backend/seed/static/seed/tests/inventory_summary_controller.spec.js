/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: inventory_summary_controller', () => {
  let $controller;
  let $rootScope;
  let $q;
  let analyses_service;
  let modal;

  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject((_$controller_, _$rootScope_, _$q_, _analyses_service_) => {
      $controller = _$controller_;
      $rootScope = _$rootScope_;
      $q = _$q_;
      analyses_service = _analyses_service_;
    });
    // updateHeight needs a registered ui-grid; skip the deferred call
    spyOn(_, 'delay');
    modal = { close: jasmine.createSpy('close') };
  });

  const create_controller = () => {
    const scope = $rootScope.$new();
    $controller('inventory_summary_controller', {
      $scope: scope,
      $stateParams: { inventory_type: 'properties' },
      $uibModal: { open: () => modal },
      urls: { static_url: '/static/' },
      inventory_service: { get_last_cycle: () => 1, save_last_cycle: () => {} },
      cycles: { cycles: [{ id: 1, name: 'Empty cycle' }] }
    });
    return scope;
  };

  // get_summary resolves with these error bodies instead of rejecting
  const error_responses = [
    ['the cycle has no properties', { success: false, message: 'No properties found for the given cycle' }, 'No properties found for the given cycle'],
    ['the permission check fails', { status: 'error', message: 'Permission denied' }, 'Permission denied'],
    ['DRF rejects the request', { detail: 'Invalid API key or Bearer Token' }, 'Invalid API key or Bearer Token'],
    ['there is no response body', undefined, 'Unable to load the summary for this cycle']
  ];

  error_responses.forEach(([description, response, message]) => {
    it(`closes the loading modal and shows a message when ${description}`, () => {
      spyOn(analyses_service, 'get_summary').and.returnValue($q.resolve(response));

      const scope = create_controller();
      scope.summaryGridOptions.data = [{ Summary: 'Total Records', Value: 5 }];
      expect(() => scope.$digest()).not.toThrow();

      expect(analyses_service.get_summary).toHaveBeenCalledWith(1);
      expect(modal.close).toHaveBeenCalled();
      expect(scope.summary_message).toBe(message);
      expect(scope.summaryGridOptions.data).toEqual([]);
      expect(scope.countGridOptions.data).toEqual([]);
    });
  });

  it('populates the grids and clears the message on success', () => {
    spyOn(analyses_service, 'get_summary').and.returnValue(
      $q.resolve({
        status: 'success',
        total_records: 2,
        number_extra_data_fields: 1,
        total_sqft: 300,
        'column_settings fields and counts': { 'Address Line 1': 2 }
      })
    );

    const scope = create_controller();
    scope.summary_message = 'stale';
    scope.$digest();

    expect(modal.close).toHaveBeenCalled();
    expect(scope.summary_message).toBeNull();
    expect(scope.summaryGridOptions.data.map((row) => row.Value)).toEqual([2, 1, 300]);
    expect(scope.countGridOptions.data).toEqual([{ Field: 'Address Line 1', Count: 2 }]);
  });
});
