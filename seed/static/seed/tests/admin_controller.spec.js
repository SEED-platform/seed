/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('controller: admin_controller', function () {
  var mock_organization_service;
  var mock_uploader_service;
  var controller, admin_controller_scope;

  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, user_service, organization_service, uploader_service, $q) {
      admin_controller_scope = $rootScope.$new();
      controller = $controller;
      mock_organization_service = organization_service;
      mock_uploader_service = uploader_service;

      spyOn(mock_organization_service, 'get_organization_users')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.reject({
            status: 'fail'
          });
        });
      spyOn(mock_organization_service, 'add_user_to_org')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.reject({
            status: 'fail'
          });
        });
      spyOn(mock_organization_service, 'remove_user')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.reject({
            status: 'fail'
          });
        });
      spyOn(mock_organization_service, 'get_organizations')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.reject({
            status: 'fail'
          });
        });
      spyOn(mock_organization_service, 'delete_organization_inventory')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve({
            status: 'success'
          });
        });
      spyOn(mock_uploader_service, 'check_progress_loop')
        .andCallFake(function (progress, num, num2, cb) {
          // return $q.reject for error scenario
          cb();
          return $q.resolve({
            status: 'success',
            progress: '100.0'
          });
        });
    });
  });

  function create_admin_controller () {
    controller('admin_controller', {
      $scope: admin_controller_scope,
      auth_payload: {
        auth: {
          requires_superuser: true
        }
      },
      organizations_payload: {
        organizations: [{
          is_parent: true,
          user_role: 'owner',
          sub_orgs: [],
          number_of_users: 1,
          id: 1,
          owners: [{first_name: 'Seed', last_name: 'User', email: 'demo@example.com', id: 1}],
          name: 'SEED',
          created: '2017-01-01',
          org_id: 1,
          user_is_owner: true,
          parent_id: 1,
          cycles: [{
            num_taxlots: 0,
            cycle_id: 1,
            num_properties: 0,
            name: '2017 Calendar Year'
          }]
        }]
      },
      user_profile_payload: {
        user: {
          status: 'success',
          api_key: '',
          first_name: 'Seed',
          last_name: 'User',
          email: 'demo@example.com'
        }
      },
      users_payload: {
        users: [{
          user_id: 1,
          email: 'demo@example.com',
          number_of_orgs: 2
        }]
      }
    });
  }

  describe('update_alert', function () {
    it('should set the show state to true', function () {
      // arrange
      create_admin_controller();

      // act
      admin_controller_scope.update_alert(true, 'test message');

      // assertions
      expect(admin_controller_scope.alert.show).toBe(true);
      expect(admin_controller_scope.alert.message).toBe('test message');
    });

    it('should raise a confirm window when the delete buildings button is clicked', function () {
      // arrange
      create_admin_controller();
      var oldConfirm = confirm;
      confirm = jasmine.createSpy();

      // act
      admin_controller_scope.confirm_inventory_delete({org_id: 44, name: 'my new org'});

      // assertions
      // spyOn(window, 'confirm').andReturn(false);
      expect(confirm).toHaveBeenCalledWith('Are you sure you want to PERMANENTLY delete \'my new org\'s properties and tax lots?');

      confirm = oldConfirm;

    });

    it('should error get orgs', function () {
      // arrange
      create_admin_controller();

      // act
      admin_controller_scope.org_user.add();
      admin_controller_scope.org_user.remove_user(admin_controller_scope.org.users[0], 1);
      admin_controller_scope.get_organizations_users(admin_controller_scope.org);
      admin_controller_scope.$digest();

      // assertions
      expect(mock_organization_service.remove_user).toHaveBeenCalled();
      expect(mock_organization_service.add_user_to_org).toHaveBeenCalled();
      expect(mock_organization_service.get_organization_users).toHaveBeenCalled();
    });

    it('should delete orgs', function () {
      // arrange
      create_admin_controller();

      // act
      admin_controller_scope.delete_org_inventory({org: 'something'});
      admin_controller_scope.$digest();

      // assertions
      expect(mock_organization_service.get_organizations).toHaveBeenCalled();
    });
  });

});
