/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
describe('controller: new_member_modal_controller', () => {
  // globals set up and used in each test scenario
  let mock_user_service;
  let controller;
  let modal_state;
  let ctrl_scope;
  beforeEach(() => {
    module('BE.seed');
    inject((_$httpBackend_) => {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $uibModal, $q, user_service) => {
      controller = $controller;
      ctrl_scope = $rootScope.$new();
      modal_state = '';

      mock_user_service = user_service;
      spyOn(mock_user_service, 'add').andCallFake(() =>
        // return $q.reject for error scenario
        $q.resolve({ status: 'success' }));
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_new_member_controller() {
    controller = controller('new_member_modal_controller', {
      $scope: ctrl_scope,
      $uibModalInstance: {
        close: () => {
          modal_state = 'close';
        },
        dismiss: () => {
          modal_state = 'dismiss';
        }
      },
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
    expect(ctrl_scope.user.role).toEqual('member');
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
      role: ctrl_scope.roles[1].value,
      organization: { organization_id: 1 }
    });
  });
});
