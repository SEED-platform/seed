/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('Controller: menu_controller', function () {
  // globals set up and used in each test scenario
  var controller;
  var menu_controller_scope;
  var mock_spinner_utility;
  // var mock_dataset_service;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, urls, $q, organization_service, user_service, dataset_service, spinner_utility) {
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
      spyOn(mock_spinner_utility, 'show')
        .andCallFake(function () {
          // Do nothing
        });
      spyOn(mock_spinner_utility, 'hide')
        .andCallFake(function () {
          // Do nothing
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_menu_controller () {
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
