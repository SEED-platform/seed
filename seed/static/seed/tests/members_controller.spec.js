/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
describe('controller: members_controller', () => {
  // globals set up and used in each test scenario
  let controller;
  let ctrl_scope;
  let mock_organization_service;

  beforeEach(() => {
    module('BE.seed');
    inject((_$httpBackend_) => {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $uibModal, $q, organization_service) => {
      controller = $controller;
      ctrl_scope = $rootScope.$new();

      mock_organization_service = organization_service;

      spyOn(mock_organization_service, 'remove_user').andCallFake(() => $q.resolve({
        status: 'success'
      }));
      spyOn(mock_organization_service, 'get_organization_users').andCallFake(() => $q.resolve({
        status: 'success',
        users: [{ id: 1, first_name: 'Bob', last_name: 'D' }]
      }));
      spyOn(mock_organization_service, 'update_role').andCallFake(() => $q.resolve({
        status: 'success'
      }));
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_members_controller() {
    controller = controller('members_controller', {
      $scope: ctrl_scope,
      users_payload: {
        users: [
          { first_name: 'J', last_name: 'S' },
          { first_name: undefined, last_name: null }
        ]
      },
      organization_payload: {
        organization: { name: 'my org', id: 4 }
      },
      auth_payload: {
        auth: {
          can_invite_member: true,
          can_remove_member: true
        }
      },
      access_level_tree: {
        access_level_names: ['my org'],
        access_level_tree: [{
          id: 1,
          data: {
            name: 'root',
            organization: 4,
            path: { 'my org': 'root' }
          }
        }]
      },
      user_profile_payload: [
        'user_service',
        (user_service) => user_service.get_user_profile()
      ]
    });
  }

  /**
   * Test scenarios
   */

  it('should accepts its payload', () => {
    // arrange
    create_members_controller();

    // act
    ctrl_scope.$digest();

    // assertions
    expect(ctrl_scope.org).toEqual({ name: 'my org', id: 4 });
    expect(ctrl_scope.users[0].name).toEqual('J S');
    expect(ctrl_scope.users[1].name).toEqual(' ');
  });

  it('clicking remove should remove a user', () => {
    // arrange
    create_members_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.remove_member({ user_id: 2 });

    // assertions
    expect(mock_organization_service.remove_user).toHaveBeenCalledWith(2, 4);

    ctrl_scope.$digest();
    expect(mock_organization_service.get_organization_users).toHaveBeenCalledWith({ org_id: 4 });
  });

  it("clicking a new role should update the user's role", () => {
    // arrange
    create_members_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.update_role({ user_id: 2, role: 'viewer' }, 'viewer');

    // assertions
    expect(mock_organization_service.update_role).toHaveBeenCalledWith(2, 4, 'viewer');
  });
});
