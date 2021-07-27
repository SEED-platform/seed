/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: update_item_labels_modal_controller', function () {
  // globals set up and used in each test scenario
  var mock_label_service, scope, controller, modal_state, mock_notification, mock_new_label_form;
  var update_controller_scope;

  var available_colors = [{
    label: 'success',
    color: 'green'
  }, {
    label: 'danger',
    color: 'red'
  }];

  var all_available_labels = [{
    color: 'green',
    is_applied: false,
    id: 70,
    name: 'new label',
    label: 'success',
    text: 'new label'
  }, {
    color: 'orange',
    is_applied: false,
    id: 44,
    name: 'data quality warning3',
    label: 'warning',
    text: 'data quality warning3'
  }, {
    color: 'red',
    is_applied: false,
    id: 43,
    name: 'data quality error!',
    label: 'danger',
    text: 'data quality error!'
  }, {
    color: 'green',
    is_applied: true,
    id: 74,
    name: 'dafdsfsa fa',
    label: 'success',
    text: 'dafdsfsa fa'
  }, {
    color: 'gray',
    is_applied: true,
    id: 66,
    name: 'abc3',
    label: 'default',
    text: 'abc3'
  }, {
    color: 'light blue',
    is_applied: true,
    id: 65,
    name: 'abc',
    label: 'info',
    text: 'abc'
  }];

  //A new label created by the user via the form
  var new_label_by_user = {
    color: 'green',
    name: 'user new label'
  };

  var return_obj_for_create_label = {
    color: 'green',
    is_applied: true,
    id: 100,
    name: 'user new label',
    label: 'default',
    text: 'user new label'
  };


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, $q, label_service, Notification) {

      controller = $controller;
      scope = $rootScope;
      update_controller_scope = $rootScope.$new();

      // mock the label_service factory methods used in the controller
      // and return their promises (if necessary).
      mock_label_service = label_service;

      spyOn(mock_label_service, 'get_labels')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve(all_available_labels);
        });
      spyOn(mock_label_service, 'create_label')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve(return_obj_for_create_label);
        });
      spyOn(mock_label_service, 'get_available_colors')
        .andCallFake(function () {
          return available_colors;
        });

      //mock the notification service
      mock_notification = Notification;
      spyOn(mock_notification, 'primary')
        .andCallFake(function () {
          // Do nothing
        });

      mock_new_label_form = {
        $dirty: false,
        $valid: true
      };
      mock_new_label_form.$setPristine = function () {
      };

      scope.form = mock_new_label_form;

    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_update_item_labels_modal_controller () {
    controller('update_item_labels_modal_controller', {
      $scope: update_controller_scope,
      $uibModalInstance: {
        close: function () {
          modal_state = 'close';
        },
        dismiss: function () {
          modal_state = 'dismiss';
        }
      },
      label_service: mock_label_service,
      inventory_ids: [],
      inventory_type: 'properties',
      notification: mock_notification
    });

  }

  /**
   * Test scenarios
   */

  it('should initialize the default "new" label', function () {

    // arrange
    create_update_item_labels_modal_controller();
    // act
    update_controller_scope.$digest();
    update_controller_scope.initialize_new_label();

    // assertions
    expect(update_controller_scope.new_label.color).toBe('gray');
    expect(update_controller_scope.new_label.label).toBe('default');
  });

  it('should create a new label and add it to labels array', function () {

    //arrange
    create_update_item_labels_modal_controller();
    //assume user entered following value on form and bindings were updated
    update_controller_scope.new_label = new_label_by_user;
    update_controller_scope.newLabelForm = mock_new_label_form;

    //act
    update_controller_scope.$digest();
    update_controller_scope.labels = all_available_labels;

    update_controller_scope.submitNewLabelForm(mock_new_label_form);

    expect(mock_label_service.create_label).toHaveBeenCalledWith(new_label_by_user);

    update_controller_scope.$digest();
    expect(update_controller_scope.labels[0]).toEqual(return_obj_for_create_label);

  });


});
