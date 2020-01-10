/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: create_sub_organization_modal_controller', function () {
  // globals set up and used in each test scenario
  var mock_organization_service, modal_state;
  var controller, ctrl_scope;
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, $q, organization_service) {
      controller = $controller;
      ctrl_scope = $rootScope.$new();
      modal_state = '';

      mock_organization_service = organization_service;
      spyOn(mock_organization_service, 'create_sub_org')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve({status: 'success'});
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_sub_organization_modal_controller () {
    controller('create_sub_organization_modal_controller', {
      $scope: ctrl_scope,
      $uibModalInstance: {
        close: function () {
          modal_state = 'close';
        },
        dismiss: function () {
          modal_state = 'dismiss';
        }
      },
      organization: {organization_id: 1}
    });
  }

  /**
   * Test scenarios
   */

  it('should call the organization service to add a new sub_org', function () {
    // arrange
    create_sub_organization_modal_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.sub_org.name = 'my shiny new org';
    ctrl_scope.sub_org.email = 'jb.smooth@be.com';
    ctrl_scope.submit_form(true);

    // assertions
    expect(mock_organization_service.create_sub_org)
      .toHaveBeenCalledWith({
        organization_id: 1
      }, {
        name: 'my shiny new org',
        email: 'jb.smooth@be.com'
      });
  });

});
