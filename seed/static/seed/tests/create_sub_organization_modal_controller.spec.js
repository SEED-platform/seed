/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
describe('controller: create_sub_organization_modal_controller', () => {
  // globals set up and used in each test scenario
  let mock_organization_service; let
    modal_state;
  let controller; let
    ctrl_scope;
  beforeEach(() => {
    module('BE.seed');
    inject((_$httpBackend_) => {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, $rootScope, $uibModal, $q, organization_service) => {
      controller = $controller;
      ctrl_scope = $rootScope.$new();
      modal_state = '';

      mock_organization_service = organization_service;
      spyOn(mock_organization_service, 'create_sub_org').andCallFake(() =>
        // return $q.reject for error scenario
        $q.resolve({ status: 'success' }));
    });
  });

  // this is outside the beforeEach so it can be configured by each unit test
  function create_sub_organization_modal_controller() {
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
      organization: { organization_id: 1 }
    });
  }

  /**
   * Test scenarios
   */

  it('should call the organization service to add a new sub_org', () => {
    // arrange
    create_sub_organization_modal_controller();

    // act
    ctrl_scope.$digest();
    ctrl_scope.sub_org.name = 'my shiny new org';
    ctrl_scope.sub_org.email = 'jb.smooth@be.com';
    ctrl_scope.submit_form(true);

    // assertions
    expect(mock_organization_service.create_sub_org).toHaveBeenCalledWith(
      {
        organization_id: 1
      },
      {
        name: 'my shiny new org',
        email: 'jb.smooth@be.com'
      }
    );
  });
});
