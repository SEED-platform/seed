/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: dataset_list_controller', function () {
  // globals set up and used in each test scenario
  var controller, $state;
  var dataset_list_controller_scope;
  var mock_uploader_service;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, urls, $q, uploader_service, _$state_) {
      controller = $controller;
      $state = _$state_;
      dataset_list_controller_scope = $rootScope.$new();

      // mock the uploader_service factory methods used in the controller
      // and return their promises
      mock_uploader_service = uploader_service;
      spyOn(mock_uploader_service, 'create_dataset')
        .andCallFake(function (dataset_name) {
          // return $q.reject for error scenario
          if (dataset_name !== 'fail') {
            return $q.resolve({
              status: 'success',
              import_record_id: 3,
              import_record_name: dataset_name
            });
          } else {
            return $q.reject({
              status: 'error',
              message: 'name already in use'
            });
          }
        });
      }
    );
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_dataset_list_controller() {
    var fake_datasets_payload = {
      status: 'success',
      datasets: [{
        name: 'DC 2013 data',
        last_modified: (new Date()).getTime(),
        last_modified_by: 'demo@seed-platform.org',
        number_of_buildings: 89
      }, {
        name: 'DC 2014 data',
        last_modified: (new Date()).getTime() - 1550 * 60 * 60 * 1000,
        last_modified_by: 'demo2@seed-platform.org',
        number_of_buildings: 70
      }]
    };
    controller('dataset_list_controller', {
      $scope: dataset_list_controller_scope,
      datasets_payload: fake_datasets_payload
    });
  }

  /**
   * Test scenarios
   */

  it('should have a dataset_payload', function () {
    // arrange
    create_dataset_list_controller();

    // act
    dataset_list_controller_scope.$digest();

    // assertions
    expect(dataset_list_controller_scope.datasets.length).toEqual(2);
  });

  it('should disable the mapping button if the dataset has no Assessor files', function () {
    // arrange
    var dataset = {
      importfiles: [{
        source_type: 'Portfolio Raw'
      }, {
        source_type: 'Portfolio Raw'
      }]
    };
    create_dataset_list_controller();

    // act
    dataset_list_controller_scope.$digest();
    var disabled = dataset_list_controller_scope.missing_assessor_files(dataset);

    // assertions
    expect(disabled).toEqual(true);
  });

  it('should enable the mapping button if the dataset has at least one' +
    ' Assessor file', function () {
    // arrange
    var dataset = {
      importfiles: [{
        source_type: 'Portfolio Raw'
      }, {
        source_type: 'Assessed Raw'
      }]
    };
    create_dataset_list_controller();

    // act
    dataset_list_controller_scope.$digest();
    var disabled = dataset_list_controller_scope.missing_assessor_files(dataset);

    // assertions
    expect(disabled).toEqual(false);
  });
  it('should disable the matching button if the dataset has no' +
    ' Portfolio Manger files', function () {
    // arrange
    var dataset = {
      importfiles: [{
        source_type: 'Assessed Raw'
      }, {
        source_type: 'Assessed Raw'
      }]
    };
    create_dataset_list_controller();

    // act
    dataset_list_controller_scope.$digest();
    var disabled = dataset_list_controller_scope.missing_pm_files(dataset);

    // assertions
    expect(disabled).toEqual(true);
  });
  it('should enable the matching button if the dataset has at least one' +
    ' Portfolio Manger file', function () {
    // arrange
    var dataset = {
      importfiles: [{
        source_type: 'Portfolio Raw'
      }, {
        source_type: 'Assessed Raw'
      }]
    };
    create_dataset_list_controller();

    // act
    dataset_list_controller_scope.$digest();
    var disabled = dataset_list_controller_scope.missing_pm_files(dataset);

    // assertions
    expect(disabled).toEqual(false);
  });
  it('should respond to URL when the ``Mapping`` button is clicked', function () {
    // arrange
    create_dataset_list_controller();

    // act
    dataset_list_controller_scope.$digest();

    // assertions
    expect($state.href('mapping', {importfile_id: 3})).toBe('#/data/mapping/3');
  });

});
