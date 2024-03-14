/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
describe('Controller: menu_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let menu_controller_scope;
  let mock_spinner_utility;
  // var mock_dataset_service;

  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(() => {
    module('BE.seed');
    inject((_$httpBackend_) => {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $uibModal, urls, $q, organization_service, user_service, dataset_service, spinner_utility) => {
      controller = $controller;
      menu_controller_scope = $rootScope.$new();
      menu_controller_scope.inventory_type = 'properties';

      // mock_dataset_service = dataset_service;
      // spyOn(mock_dataset_service, 'get_matching_results')
      //   .andCallFake(function (import_file) {
      //     // return $q.reject for error scenario
      //     return $q.resolve({
      //       properties: {
      //         status: 'success',
      //         matched: 10,
      //         unmatched: 5,
      //         duplicates: 0
      //       }
      //     });
      //   });

      mock_spinner_utility = spinner_utility;
      spyOn(mock_spinner_utility, 'show').andCallFake(() => {
        // Do nothing
      });
      spyOn(mock_spinner_utility, 'hide').andCallFake(() => {
        // Do nothing
      });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_menu_controller() {
    controller('menu_controller', {
      $scope: menu_controller_scope,
      $stateParams: {
        cycle_id: 2017,
        inventory_id: 4,
        inventory_type: 'properties',
        import_file_id: 1
      }
    });
  }

  /**
   * Test scenarios
   */

  // it('should have a buildings payload with potential matches', function () {
  //   // arrange
  //   create_menu_controller();
  //
  //   // act
  //   menu_controller_scope.$digest();
  //
  //   menu_controller_scope.$broadcast('$stateChangeError');
  //   menu_controller_scope.$broadcast('$stateNotFound');
  //   menu_controller_scope.$broadcast('app_error', {data: 'something'});
  //   menu_controller_scope.is_active('/seed/data');
  //   // expect(menu_controller_scope.href("/something")).toBe(1);
  //   menu_controller_scope.is_initial_state();
  //   menu_controller_scope.open_data_upload_modal();
  //
  //
  //   // assertions
  //   expect(1).toEqual(1);
  // });
});
