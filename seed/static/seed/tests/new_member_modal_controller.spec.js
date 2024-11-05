/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
describe('controller: new_member_modal_controller', () => {
  // globals set up and used in each test scenario
  let mock_user_service;
  let controller;
  let ctrl_scope;
  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $uibModal, $q, user_service) => {
      controller = $controller;
      ctrl_scope = $rootScope.$new();

      mock_user_service = user_service;
      spyOn(mock_user_service, 'add').andCallFake(() => $q.resolve({ status: 'success' }));
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_new_member_controller() {
    controller = controller('new_member_modal_controller', {
      $scope: ctrl_scope,
      $uibModalInstance: {},
      organization: { organization_id: 1 },
      access_level_tree: [{
        id: '1',
        data: {
          name: 'root',
          organization: '1',
          path: { 'my org': 'root' }
        }
      }],
      level_names: ['my org']
    });
  }

  /**
   * Test scenarios
   */

  it('should set the default role to "member"', () => {
    // arrange
    create_new_member_controller();

    // act
    ctrl_scope.$digest();

    // assertions
    expect(ctrl_scope.user.role).toEqual(ctrl_scope.roles.MEMBER);
  });

  it('should call the user service to add a new user to the org', () => {
    // arrange
    create_new_member_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.user.first_name = 'JB';
    ctrl_scope.user.last_name = 'Smooth';
    ctrl_scope.user.email = 'jb.smooth@be.com';
    ctrl_scope.submit_form(true);

    // assertions
    expect(mock_user_service.add).toHaveBeenCalledWith({
      first_name: 'JB',
      last_name: 'Smooth',
      email: 'jb.smooth@be.com',
      role: ctrl_scope.roles.MEMBER,
      organization: { organization_id: 1 }
    });
  });
});
