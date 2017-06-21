/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: data_upload_modal_controller', function () {
  // globals set up and used in each test scenario
  var mock_uploader_service, scope, controller, modal_state;
  var data_upload_modal_controller, data_upload_controller_scope, modalInstance, labels;
  var deleted_label, updated_label, mock_mapping_service, mock_matching_service;
  var global_step = 1;
  var global_dataset = {};
  var return_labels = [{
    name: 'compliant',
    color: 'green',
    id: 1
  }, {
    name: 'new label',
    color: 'blue',
    id: 2
  }];

  var cycles = {
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

  var organization = {
    id: 1
  };
  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(
    function ($controller, $rootScope, $uibModal, urls, $q, uploader_service, mapping_service, matching_service) {
      controller = $controller;
      scope = $rootScope;
      data_upload_controller_scope = $rootScope.$new();
      modal_state = '';

      // mock the uploader_service factory methods used in the controller
      // and return their promises
      mock_uploader_service = uploader_service;
      mock_mapping_service = mapping_service;
      mock_matching_service = matching_service;
      spyOn(mock_uploader_service, 'get_AWS_creds')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.when({
            status: 'success',
            AWS_CLIENT_ACCESS_KEY: '123',
            AWS_UPLOAD_BUCKET_NAME: 'test-bucket'
          });
        }
        );
      spyOn(mock_uploader_service, 'check_progress')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.when({
            status: 'success',
            progress: '25.0'
          });
        });
      spyOn(mock_uploader_service, 'check_progress_loop')
        .andCallFake(function (progress, num, num2, cb) {
          // return $q.reject for error scenario
          cb();
          return $q.when({
            status: 'success',
            progress: '100.0'
          });
        });
      spyOn(mock_uploader_service, 'create_dataset')
        .andCallFake(function (dataset_name) {
          // return $q.reject for error scenario
          if (dataset_name !== 'fail') {
            return $q.when({
              status: 'success',
              id: 3,
              name: dataset_name

            });
          } else {
            return $q.reject({
              status: 'error',
              message: 'name already in use'
            });
          }
        });
      spyOn(mock_uploader_service, 'save_raw_data')
        .andCallFake(function (dataset_name) {
          // return $q.reject for error scenario
          if (dataset_name !== 'fail') {
            return $q.when({
              status: 'success',
              file_id: 3,
              progress_key: ':1:SEED:save_raw_data:PROG:51'
            });
          } else {
            return $q.reject({
              status: 'error'
            });
          }
        });
      spyOn(mock_mapping_service, 'start_mapping')
        .andCallFake(function (dataset_name) {
          // return $q.reject for error scenario
          if (dataset_name !== 'fail') {
            return $q.when({
              status: 'success',
              file_id: 3
            });
          } else {
            return $q.reject({
              status: 'error'
            });
          }
        });
      spyOn(mock_matching_service, 'start_system_matching')
        .andCallFake(function (file_id) {
          // return $q.reject for error scenario
          return $q.when({
            status: 'warning',
            file_id: 3
          });
        });

    }
  ));

  // this is outside the beforeEach so it can be configured by each unit test
  function create_data_upload_modal_controller () {
    data_upload_modal_controller = controller('data_upload_modal_controller', {
      $scope: data_upload_controller_scope,
      $uibModalInstance: {
        close: function () {
          modal_state = 'close';
        },
        dismiss: function () {
          modal_state = 'dismiss';
        }
      },
      step: global_step,
      dataset: global_dataset,
      cycles: cycles,
      organization: organization
    });
  }

  /**
   * Test scenarios
   */

  it('should close the modal when the close function is called', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.close();
    data_upload_controller_scope.$digest();

    // assertions
    expect(modal_state).toBe('close');
  });

  it('should cancel the modal when the cancel function is called', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.cancel();
    data_upload_controller_scope.$digest();

    // assertions
    expect(modal_state).toBe('dismiss');
  });

  it('should start at the step provided', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.step.number).toBe(1);

    // arrange
    global_step = 2;
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.step.number).toBe(2);
  });

  it('should goto different steps', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    var step;
    step = 2;
    data_upload_controller_scope.goto_step(step);
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.step.number).toBe(step);
  });

  it('disables the \'Name it\' button if no text is entered', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.disabled()).toBe(true);
  });
  it('disables the \'Name it\' button if no text is entered, then cleared', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.dataset.name = undefined;
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.disabled()).toBe(true);
  });
  it('enables the \'Name it\' button if text is entered', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.dataset.name = 'my dataset name';
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.disabled()).toBe(false);
  });
  it('should show an alert if the dataset name is already in use', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.create_dataset('fail');
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.alert).toBe(true);
  });
  it('should not show an alert if the dataset name is not already in use', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.create_dataset('my shiny new dataset');
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.alert).toBe(false);
  });
  it('after creating a dataset, stores the dataset id', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    var ds_name = 'my shiny new dataset';
    data_upload_controller_scope.create_dataset(ds_name);
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.id).toBe(3);
    expect(data_upload_controller_scope.dataset.name).toBe(ds_name);
  });
  it('after uploading a file, stores the file id', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    var message, filename;
    message = 'upload_complete';
    filename = 'file1.csv';

    // act
    data_upload_controller_scope.uploaderfunc(message, {
      filename: filename,
      file_id: 20140313,
      cycle_id: cycles.cycles[0].id
    });
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.import_file_id).toBe(20140313);
  });
  it('should show an invalid extension alert if a file with an invalid' +
    'extension is loaded', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.uploaderfunc('invalid_extension');
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.uploader.invalid_extension_alert)
      .toBe(true);
  });
  it('should hide the upload button after the user selects a file', function () {
    // arrange
    create_data_upload_modal_controller();
    var message, filename;
    message = 'upload_submitted';
    filename = 'file1.csv';

    // act
    data_upload_controller_scope.uploaderfunc(message, {filename: filename});
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.filename).toBe(filename);
    expect(data_upload_controller_scope.uploader.in_progress).toBe(true);
  });
  it('should show the progressbar during upload', function () {
    // arrange
    create_data_upload_modal_controller();
    var message, filename, progress;
    message = 'upload_in_progress';
    filename = 'file1.csv';
    progress = {
      loaded: 10,
      total: 100
    };

    // act
    data_upload_controller_scope.uploaderfunc(message, filename, progress);
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.uploader.in_progress).toBe(true);
    expect(data_upload_controller_scope.uploader.progress).toBe(2.5);
  });
  it('should start saving the energy data when the file has been uploaded', function () {
    // arrange
    create_data_upload_modal_controller();
    var message, filename;
    message = 'upload_complete';
    file = {
      filename: 'file1.csv',
      file_id: 1234,
      cycle_id: "myCycle",
    }
    data_upload_controller_scope.step.number = 4;

    // act
    data_upload_controller_scope.uploaderfunc(message, file);
    data_upload_controller_scope.$digest();

    // assertions
    expect(mock_uploader_service.save_raw_data).toHaveBeenCalledWith(1234, "myCycle")
    expect(mock_uploader_service.check_progress_loop).toHaveBeenCalled();
    expect(mock_mapping_service.start_mapping).toHaveBeenCalledWith(1234);
    expect(mock_matching_service.start_system_matching).toHaveBeenCalledWith(1234);
    expect(data_upload_controller_scope.uploader.status_message)
      .toBe('auto-matching energy data');
  });

  it('should test find matches', function () {
    // arrange
    create_data_upload_modal_controller();
    data_upload_controller_scope.dataset.import_file_id = 1234;

    // act
    data_upload_controller_scope.find_matches();
    data_upload_controller_scope.$digest();

    // assertions
    expect(mock_matching_service.start_system_matching).toHaveBeenCalledWith(1234);
  });

  it('should take an dataset payload', function () {
    // arrange
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.name).toBe('');
    expect(data_upload_controller_scope.dataset.filename).toBe('');
    expect(data_upload_controller_scope.dataset.id).toBe(0);
  });

  it('should extend a custom dataset payload', function () {
    // arrange
    global_dataset = {
      id: 100,
      filename: 'seed_data.csv',
      name: 'Compliance Project'
    };
    create_data_upload_modal_controller();

    // act
    data_upload_controller_scope.$digest();

    // assertions
    expect(data_upload_controller_scope.dataset.name).toBe('Compliance Project');
    expect(data_upload_controller_scope.dataset.filename).toBe('seed_data.csv');
    expect(data_upload_controller_scope.dataset.id).toBe(100);
    expect(data_upload_controller_scope.dataset.alert).toBe(false);

  });
});
