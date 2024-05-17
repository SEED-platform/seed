/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: data_quality_modal_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let data_quality_controller_scope;

  const dataQualityResults = [{
    id: 2311243,
    address_line_1: '25374 S Melon Street',
    custom_id_1: null,
    pm_property_id: null,
    data_quality_results: [{
      field: 'custom_id_1',
      formatted_field: 'Custom ID 1',
      value: null,
      table_name: 'PropertyState',
      message: 'Custom ID 1 is null',
      detailed_message: 'Custom ID 1 is null',
      severity: 'error',
      condition: 'not_null'
    }, {
      field: 'pm_property_id',
      formatted_field: 'PM Property ID',
      value: null,
      table_name: 'PropertyState',
      message: 'PM Property ID is null',
      detailed_message: 'PM Property ID is null',
      severity: 'error',
      condition: 'not_null'
    }]
  }, {
    id: 2311244,
    address_line_1: '139173 N Mandarin Avenue',
    custom_id_1: null,
    pm_property_id: null,
    data_quality_results: [{
      field: 'custom_id_1',
      formatted_field: 'Custom ID 1',
      value: null,
      table_name: 'PropertyState',
      message: 'Custom ID 1 is null',
      detailed_message: 'Custom ID 1 is null',
      severity: 'error',
      condition: 'not_null'
    }, {
      field: 'pm_property_id',
      formatted_field: 'PM Property ID',
      value: null,
      table_name: 'PropertyState',
      message: 'PM Property ID is null',
      detailed_message: 'PM Property ID is null',
      severity: 'error',
      condition: 'not_null'
    }]
  }, {
    id: 2311245,
    address_line_1: '187329 SE Citron Lane',
    custom_id_1: null,
    pm_property_id: null,
    data_quality_results: [{
      field: 'custom_id_1',
      formatted_field: 'Custom ID 1',
      value: null,
      table_name: 'PropertyState',
      message: 'Custom ID 1 is null',
      detailed_message: 'Custom ID 1 is null',
      severity: 'error',
      condition: 'not_null'
    }, {
      field: 'pm_property_id',
      formatted_field: 'PM Property ID',
      value: null,
      table_name: 'PropertyState',
      message: 'PM Property ID is null',
      detailed_message: 'PM Property ID is null',
      severity: 'error',
      condition: 'not_null'
    }]
  }];

  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(() => {
    module('BE.seed');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope) => {
      controller = $controller;
      data_quality_controller_scope = $rootScope.$new();
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_data_quality_modal_controller() {
    controller('data_quality_modal_controller', {
      $scope: data_quality_controller_scope,
      $uibModalInstance: {},
      dataQualityResults,
      name: null,
      uploaded: null,
      run_id: 1,
      orgId: 1
    });
  }

  /**
   * Test scenarios
   */

  /*  set this up but doesn't do anything currently */
  // eslint-disable-next-line func-names
  it('should dq modal sort and search', function () {
    // arrange
    create_data_quality_modal_controller();

    // act
    data_quality_controller_scope.sortable = true;
    data_quality_controller_scope.$digest();

    // assertions
    data_quality_controller_scope.search.column_prototype.toggle_sort();

    data_quality_controller_scope.search.sort_column = this.sort_column;
    data_quality_controller_scope.$digest();

    // assertions
    data_quality_controller_scope.search.column_prototype.toggle_sort();
    data_quality_controller_scope.search.column_prototype.sorted_class();

    data_quality_controller_scope.search.sort_reverse = true;
    data_quality_controller_scope.$digest();

    // assertions
    data_quality_controller_scope.search.column_prototype.toggle_sort();
    data_quality_controller_scope.search.column_prototype.sorted_class();
  });
});
