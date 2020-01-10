/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: dataset_detail_controller', function () {
  // globals set up and used in each test scenario
  var controller, delete_called;
  var mock_dataset_service, dataset_detail_controller_scope;

  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, urls, $q, dataset_service) {
      controller = $controller;
      dataset_detail_controller_scope = $rootScope.$new();
      delete_called = false;

      // mock the dataset_service factory methods used in the controller
      // and return their promises
      mock_dataset_service = dataset_service;
      spyOn(mock_dataset_service, 'get_dataset')
        .andCallFake(function () {
          // return $q.reject for error scenario
          var fake_importfiles = [{
            name: 'DC_CoveredBuildings_50k.csv',
            number_of_buildings: 511,
            number_of_mappings: 511,
            number_of_cleanings: 1349,
            source_type: 'Assessed Raw',
            number_of_matchings: 403
          }, {
            name: 'DC_ESPM_Report.csv',
            number_of_buildings: 511,
            number_of_matchings: 403,
            source_type: 'Portfolio Raw'
          }];
          var fake_dataset = {
            name: 'DC 2013 data',
            last_modified: (new Date()).getTime(),
            last_modified_by: 'demo@seed-platform.org',
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
          // console.log({delete_called: delete_called, ds: fake_payload});
          return $q.resolve(fake_payload);
        });

      spyOn(mock_dataset_service, 'delete_file')
        .andCallFake(function () {
          delete_called = true;
          // console.log({d: 'delete_called'});
          return $q.resolve({
            status: 'success'
          });
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_dataset_detail_controller () {
    var fake_importfiles = [{
      name: 'DC_CoveredBuildings_50k.csv',
      number_of_buildings: 511,
      number_of_mappings: 511,
      number_of_cleanings: 1349,
      source_type: 'Assessed Raw',
      number_of_matchings: 403
    }, {
      name: 'DC_ESPM_Report.csv',
      number_of_buildings: 511,
      number_of_matchings: 403,
      source_type: 'Portfolio Raw'
    }];
    var fake_dataset = {
      name: 'DC 2013 data',
      last_modified: (new Date()).getTime(),
      last_modified_by: 'demo@seed-platform.org',
      number_of_buildings: 89,
      id: 1,
      importfiles: fake_importfiles
    };
    var fake_payload = {
      status: 'success',
      dataset: fake_dataset
    };
    var fake_cycles = {
      cycles: [{
        end: '2015-01-01T07:59:59Z',
        id: 2017,
        name: '2014 Calendar Year',
        num_properties: 1496,
        num_taxlots: 1519,
        start: '2014-01-01T08:00:00Z'
      }],
      status: 'success'
    };
    controller('dataset_detail_controller', {
      $scope: dataset_detail_controller_scope,
      cycles: fake_cycles,
      dataset_payload: fake_payload
    });
  }

  /**
   * Test scenarios
   */
  it('should have an data set payload with import files', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    dataset_detail_controller_scope.$digest();

    // assertions
    expect(dataset_detail_controller_scope.dataset.importfiles.length).toBe(2);
  });

});
