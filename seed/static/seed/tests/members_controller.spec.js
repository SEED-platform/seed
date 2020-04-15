/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: members_controller', function () {
  // globals set up and used in each test scenario
  var controller;
  var ctrl_scope;
  var mock_organization_service;

  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, $q, organization_service) {
      controller = $controller;
      ctrl_scope = $rootScope.$new();

      mock_organization_service = organization_service;

      spyOn(mock_organization_service, 'remove_user')
        .andCallFake(function () {
          return $q.resolve({
            status: 'success'
          });
        });
      spyOn(mock_organization_service, 'get_organization_users')
        .andCallFake(function () {
          return $q.resolve({
            status: 'success',
            users: [{id: 1, first_name: 'Bob', last_name: 'D'}]
          });
        });
      spyOn(mock_organization_service, 'update_role')
        .andCallFake(function () {
          return $q.resolve({
            status: 'success'
          });
        });
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_members_controller () {
    controller = controller('members_controller', {
      $scope: ctrl_scope,
      users_payload: {
        users: [
          {first_name: 'J', last_name: 'S'},
          {first_name: undefined, last_name: null}
        ]
      },
      organization_payload: {
        organization: {name: 'my org', id: 4}
      },
      auth_payload: {
        auth: {
          can_invite_member: true,
          can_remove_member: true
        }
      },
      user_profile_payload: ['user_service', function (user_service) {
        return user_service.get_user_profile();
      }]
    });
  }

  /**
   * Test scenarios
   */

  it('should accepts its payload', function () {
    // arrange
    create_members_controller();

    // act
    ctrl_scope.$digest();

    // assertions
    expect(ctrl_scope.org).toEqual({name: 'my org', id: 4});
    expect(ctrl_scope.users[0].name).toEqual('J S');
    expect(ctrl_scope.users[1].name).toEqual(' ');
  });

  it('clicking remove should remove a user', function () {
    // arrange
    create_members_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.remove_member({user_id: 2});

    // assertions
    expect(mock_organization_service.remove_user)
      .toHaveBeenCalledWith(2, 4);

    ctrl_scope.$digest();
    expect(mock_organization_service.get_organization_users)
      .toHaveBeenCalledWith({org_id: 4});
  });

  it('clicking a new role should update the user\'s role', function () {
    // arrange
    create_members_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.update_role({user_id: 2, role: 'viewer'});

    // assertions
    expect(mock_organization_service.update_role)
      .toHaveBeenCalledWith(2, 4, 'viewer');
  });
});
