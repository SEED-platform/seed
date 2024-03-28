/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: data_quality_modal_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let modal_state;
  let data_quality_controller_scope;

  const cycles = {
    cycles: [
      {
        end: '2015-01-01',
        id: 2017,
        name: '2014 Calendar Year',
        num_properties: 1496,
        num_taxlots: 1519,
        start: '2014-01-01'
      }
    ],
    status: 'success'
  };

  const organization = {
    id: 1
  };
  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(() => {
    module('BE.seed');
    inject((_$httpBackend_) => {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope /* , $q, search_service */) => {
      controller = $controller;
      data_quality_controller_scope = $rootScope.$new();
      modal_state = '';
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_data_quality_modal_controller() {
    controller('data_quality_modal_controller', {
      $scope: data_quality_controller_scope,
      $uibModalInstance: {
        close: function () {
          modal_state = 'close';
        },
        dismiss: function () {
          modal_state = 'dismiss';
        }
      },
      cycles,
      organization
    });
  }

  /**
   * Test scenarios
   */

  /*  set this up but doesn't do anything anyway, tested in e2e now. Kept file in case it's useful later */
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

    // what needs to be asserted here?
    expect(true).toBe(true);
  });
});
