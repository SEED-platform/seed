/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe("controller: members_controller", function(){
    // globals set up and used in each test scenario
    var mockService, scope, controller;
    var ctrl, ctrl_scope, modalInstance;
    var mock_organization_service;

    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function(
          $controller,
          $rootScope,
          $uibModal,
          $q,
          organization_service) {
            ctrl = $controller;
            scope = $rootScope;
            ctrl_scope = $rootScope.$new();

            mock_organization_service = organization_service;
            
            spyOn(mock_organization_service, "remove_user")
                .andCallFake(function(user_id, org_id){
                    return $q.when(
                        {
                            "status": "success"
                        }
                    );
                }
            );
            spyOn(mock_organization_service, "get_organization_users")
                .andCallFake(function(org){
                    return $q.when(
                        {
                            "status": "success",
                            "users": [{id:1, first_name:"Bob", last_name:"D"}]
                        }
                    );
                }
            );
            spyOn(mock_organization_service, "update_role")
                .andCallFake(function(org_id, user_id, role){
                    return $q.when(
                        {
                            "status": "success"
                        }
                    );
                }
            );
        }
    ));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_members_controller(){
        ctrl = ctrl('members_controller', {
            $scope: ctrl_scope,
            users_payload: {users: [
                {first_name: 'J', last_name: 'S'},
                {first_name: undefined, last_name: null}
            ]},
            organization_payload: {
                organization: {name: 'my org', id: 4}
            },
            auth_payload: {
                auth: {
                    'can_invite_member': true,
                    'can_remove_member': true
                }
            }
        });
    }

    /*
     * Test scenarios
     */

    it("should accepts its payload", function() {
        // arrange
        create_members_controller();

        // act
        ctrl_scope.$digest();

        // assertions
        expect(ctrl_scope.org).toEqual({name : 'my org', id : 4});
        expect(ctrl_scope.users[0].name).toEqual("J S");
        expect(ctrl_scope.users[1].name).toEqual(" ");
    });
    it("clicking remove should remove a user", function() {
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
    it("clicking a new role should update the user's role", function() {
        // arrange
        create_members_controller();

        // act
        ctrl_scope.$digest();
        ctrl_scope.update_role({user_id: 2, role: "viewer"});

        // assertions
        expect(mock_organization_service.update_role)
            .toHaveBeenCalledWith(2, 4, 'viewer');
    });
});
