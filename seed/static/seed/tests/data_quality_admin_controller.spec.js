/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: data_quality_admin_controller', function () {
  // globals set up and used in each test scenario
  var mockService, scope, controller, modal_state;
  var data_quality_admin_controller, data_quality_admin_controller_scope, modalInstance, labels;
  var mock_columns_provider, mock_organization_service, mock_data_quality_service;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(
    function ($controller, $rootScope, $uibModal, urls, $q, 
            // columns,
            // organization_payload,
            // data_quality_rules_payload,
            // auth_payload,
            // labels_payload,
            // data_quality_service,
            // organization_service,
            // label_service,
            spinner_utility
            ) {
      controller = $controller;
      scope = $rootScope;
      data_quality_admin_controller_scope = $rootScope.$new();
      // mock_columns_service = [];
      // mock_organization_service = [];
      // mock_data_quality_service = [];

      // mock the uploader_service factory methods used in the controller
      // and return their promises
      // spyOn(mock_uploader_service, 'get_AWS_creds')
      //   .andCallFake(function () {
      //     // return $q.reject for error scenario
      //     return $q.when({
      //       status: 'success',
      //       AWS_CLIENT_ACCESS_KEY: '123',
      //       AWS_UPLOAD_BUCKET_NAME: 'test-bucket'
      //     });
      //   });
      // spyOn(mock_uploader_service, 'create_dataset')
      //   .andCallFake(function (dataset_name) {
      //     // return $q.reject for error scenario
      //     if (dataset_name !== 'fail') {
      //       return $q.when({
      //         status: 'success',
      //         import_record_id: 3,
      //         import_record_name: dataset_name
      //       });
      //     } else {
      //       return $q.reject({
      //         status: 'error',
      //         message: 'name already in use'
      //       });
      //     }
      //   });
    }
  ));

  // this is outside the beforeEach so it can be configured by each unit test
  function create_data_quality_admin_controller () {
    var col_payload = [
      { 
      dataType:"string",
      displayName:"Address Line 1 (Property)",
      name:"address_line_1",
      table:"PropertyState",
      type:"numberStr",
      }
    ]
    data_quality_admin_controller = controller('data_quality_admin_controller', {
      $scope: data_quality_admin_controller_scope,
      columns: col_payload,
      organization_payload: {},
      data_quality_rules_payload: {},
      auth_payload: {},
      labels_payload: {}
    });
  }

  /**
   * Test scenarios
   */

  it('should have a check dq rule changes', function () {
    // arrange
    create_data_quality_admin_controller();
    var ruleGroups = {
      properties: {
        address_line_1: [{
          autofocus:true,
          data_type:"date",
          enabled:true,
          field:"address_line_1",
          label:1234,
          max:null,
          min:null,
          not_null:true,
          required:false,
          rule_type:1,
          severity:"error",
          text_match:null,
          units:""
          },
          {
          autofocus:true,
          data_type:"number",
          enabled:true,
          field:"address_line_1",
          label:null,
          max:null,
          min:null,
          not_null:true,
          required:false,
          rule_type:1,
          severity:"error",
          text_match:null,
          units:""
          }
        ]
      }
    };
    data_quality_admin_controller_scope.ruleGroups = ruleGroups;
    data_quality_admin_controller_scope.inventory_type = "properties";
    // act
    data_quality_admin_controller_scope.change_field(ruleGroups.properties.address_line_1[0], "address_line_1", 0);
    data_quality_admin_controller_scope.change_data_type(ruleGroups.properties.address_line_1[0], "string");
    data_quality_admin_controller_scope.change_required(ruleGroups.properties.address_line_1[0]);
    data_quality_admin_controller_scope.removeLabelFromRule(ruleGroups.properties.address_line_1[0]);
    data_quality_admin_controller_scope.selectAll();

    data_quality_admin_controller_scope.$digest();

    // assertions
    expect(data_quality_admin_controller_scope.ruleGroups.properties.address_line_1[0].label).toEqual(null);
    expect(data_quality_admin_controller_scope.ruleGroups.properties.address_line_1[0].required).toEqual(true);
    expect(data_quality_admin_controller_scope.ruleGroups.properties.address_line_1[0].data_type).toEqual("number");
    expect(data_quality_admin_controller_scope.ruleGroups.properties.address_line_1[0].enabled).toEqual(false);
  });
});
