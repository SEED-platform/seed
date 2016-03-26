/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe('controller: new_member_modal_ctrl', function(){
    // globals set up and used in each test scenario
    var mock_user_service, scope, controller, modal_state;
    var ctrl, ctrl_scope, modalInstance, timeout;
    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(function($controller, $rootScope, $uibModal, $q, user_service, $timeout) {
        ctrl = $controller;
        scope = $rootScope;
        ctrl_scope = $rootScope.$new();
        modal_state = '';
        timeout = $timeout;

        mock_user_service = user_service;
        spyOn(mock_user_service, 'add')
            .andCallFake(function(user){
                // return $q.reject for error scenario
                return $q.when({status: 'success'});
            }
        );
    }));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_new_member_controller(){
        ctrl = ctrl('new_member_modal_ctrl', {
            $scope: ctrl_scope,
            $uibModalInstance: {
                close: function() {
                    modal_state = 'close';
                },
                dismiss: function() {
                    modal_state = 'dismiss';
                }
            },
            organization: {organization_id: 1}
        });
    }

    /*
     * Test scenarios
     */

    it('should set the default role to \'member\'', function() {
        // arrange
        create_new_member_controller();

        // act
        ctrl_scope.$digest();

        // assertions
        expect(ctrl_scope.user.role.value).toEqual('member');
    });
    it('should call the user service to add a new user to the org',
        function() {
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
