/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: new_member_modal_controller', function () {
  // globals set up and used in each test scenario
  var mock_user_service, controller, modal_state;
  var ctrl_scope;
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, $q, user_service) {
      controller = $controller;
      ctrl_scope = $rootScope.$new();
      modal_state = '';

      mock_user_service = user_service;
      spyOn(mock_user_service, 'add')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve({status: 'success'});
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_new_member_controller () {
    controller = controller('new_member_modal_controller', {
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

  it('should set the default role to "member"', function () {
    // arrange
    create_new_member_controller();

    // act
    ctrl_scope.$digest();

    // assertions
    expect(ctrl_scope.user.role.value).toEqual('member');
  });

  it('should call the user service to add a new user to the org',
    function () {
      // arrange
      create_new_member_controller();

      // act
      ctrl_scope.$digest();
      ctrl_scope.user.first_name = 'JB';
      ctrl_scope.user.last_name = 'Smooth';
      ctrl_scope.user.email = 'jb.smooth@be.com';
      ctrl_scope.submit_form(true);

      // assertions
      expect(mock_user_service.add)
        .toHaveBeenCalledWith({
          first_name: 'JB',
          last_name: 'Smooth',
          email: 'jb.smooth@be.com',
          role: ctrl_scope.roles[0],
          organization: {
            organization_id: 1
          }
        });
    });

});
