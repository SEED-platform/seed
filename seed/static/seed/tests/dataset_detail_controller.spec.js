/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe('controller: dataset_detail_controller', function () {
  // globals set up and used in each test scenario
  var mockService, scope, controller, ngFilter, delete_called;
  var dataset_detail_controller, dataset_detail_controller_scope, modalInstance, labels;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(
    function ($controller, $rootScope, $uibModal, urls, $q, dataset_service, $filter) {
      controller = $controller;
      scope = $rootScope;
      ngFilter = $filter;
      dataset_detail_controller_scope = $rootScope.$new();
      modal_state = '';
      delete_called = false;

      // mock the dataset_service factory methods used in the controller
      // and return their promises
      mock_dataset_service = dataset_service;
      spyOn(mock_dataset_service, 'get_dataset')
        .andCallFake(function (dataset_id) {
            // return $q.reject for error scenario
            var fake_importfiles = [
              {
                name: 'DC_CoveredBuildings_50k.csv',
                number_of_buildings: 511,
                number_of_mappings: 511,
                number_of_cleanings: 1349,
                source_type: 'Assessed Raw',
                number_of_matchings: 403
              },
              {
                name: 'DC_ESPM_Report.csv',
                number_of_buildings: 511,
                number_of_matchings: 403,
                source_type: 'Portfolio Raw'
              }
            ];
            var fake_dataset = {
              name: 'DC 2013 data',
              last_modified: (new Date()).getTime(),
              last_modified_by: 'john.s@buildingenergy.com',
              number_of_buildings: 89,
              id: 1,
              importfiles: fake_importfiles
            };
            var fake_payload = {
              status: 'success',
              dataset: fake_dataset
            };
            if (delete_called) {
              fake_payload.dataset.importfiles.pop();
            }
            console.log({delete_called: delete_called, ds: fake_payload});
            return $q.when(fake_payload);
          }
        );

      spyOn(mock_dataset_service, 'delete_file')
        .andCallFake(function (import_file) {
            delete_called = true;
            console.log({d: 'delete_called'});
            return $q.when(
              {
                status: 'success'
              }
            );
          }
        );
    }
  ));

  // this is outside the beforeEach so it can be configured by each unit test
  function create_dataset_detail_controller() {
    var fake_importfiles = [
      {
        name: 'DC_CoveredBuildings_50k.csv',
        number_of_buildings: 511,
        number_of_mappings: 511,
        number_of_cleanings: 1349,
        source_type: 'Assessed Raw',
        number_of_matchings: 403
      },
      {
        name: 'DC_ESPM_Report.csv',
        number_of_buildings: 511,
        number_of_matchings: 403,
        source_type: 'Portfolio Raw'
      }
    ];
    var fake_dataset = {
      name: 'DC 2013 data',
      last_modified: (new Date()).getTime(),
      last_modified_by: 'john.s@buildingenergy.com',
      number_of_buildings: 89,
      id: 1,
      importfiles: fake_importfiles
    };
    var fake_payload = {
      status: 'success',
      dataset: fake_dataset
    };
    dataset_detail_controller = controller('dataset_detail_controller', {
      $scope: dataset_detail_controller_scope,
      dataset_payload: fake_payload
    });
  }

  /*
   * Test scenarios
   */
   // Tested in e2e
   
  // it('should have an data set payload with import files', function () {
  //   // arrange
  //   create_dataset_detail_controller();

  //   // act
  //   dataset_detail_controller_scope.$digest();

  //   // assertions
  //   expect(dataset_detail_controller_scope.dataset.importfiles.length).toBe(2);
  // });

  // it('should show an alert when the delete icon is clicked', function () {
  //   // arrange
  //   create_dataset_detail_controller();

  //   // act
  //   dataset_detail_controller_scope.$digest();
  //   var importfiles = dataset_detail_controller_scope.dataset.importfiles;
  //   dataset_detail_controller_scope.confirm_delete(importfiles[0]);
  //   dataset_detail_controller_scope.$digest();

  //   // assertions
  //   expect(dataset_detail_controller_scope.dataset.importfiles.length).toBe(1);
  // });

});
