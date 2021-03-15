/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: organization_settings_controller', function () {
  // globals set up and used in each test scenario
  var controller;
  var ctrl_scope;
  var mock_organization_service;
  var mock_meters_service;

  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, $q, organization_service, meters_service) {
      controller = $controller;
      ctrl_scope = $rootScope.$new();

      mock_organization_service = organization_service;
      mock_meters_service = meters_service;

      spyOn(mock_organization_service, 'save_org_settings')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve({
            status: 'success'
          });
        });

      spyOn(mock_meters_service, 'valid_energy_types_units')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve({
            status: 'success'
          });
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_settings_controller () {
    controller('organization_settings_controller', {
      $scope: ctrl_scope,
      all_columns: {
        fields: [
          {checked: false, title: 'PM Property ID', sort_column: 'pm_property_id'},
          {checked: false, title: 'G', sort_column: 'g'},
          {checked: false, title: 'Gross Floor Area', sort_column: 'gross_floor_area'}
        ]
      },
      organization_payload: {
        organization: {name: 'my org', id: 4}
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
          }]
      },
      auth_payload: {
        auth: {
          is_owner: true,
          is_parent_org_owner: false
        }
      },
      property_column_names: { 'column_name': 'test', 'display_name': 'test' },
      taxlot_column_names: { 'column_name': 'test', 'display_name': 'test' }
    });
  }

  /**
   * Test scenarios
   */

  it('should accepts its payload', function () {
    // arrange
    create_settings_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.save_settings();
    ctrl_scope.$digest();

    // assertions
    expect(ctrl_scope.org).toEqual({
      name: 'my org',
      id: 4
      // query_threshold: 10
    });
    expect(mock_organization_service.save_org_settings).toHaveBeenCalledWith(ctrl_scope.org);
    expect(mock_meters_service.valid_energy_types_units).toHaveBeenCalled();
    expect(ctrl_scope.settings_updated).toEqual(true);
    // expect(ctrl_scope.fields[0].checked).toEqual(true);
    // expect(ctrl_scope.fields[1].checked).toEqual(false);
    // expect(ctrl_scope.fields[0].title).toEqual('PM Property ID');
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
