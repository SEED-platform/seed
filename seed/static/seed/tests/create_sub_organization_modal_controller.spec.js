/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe('controller: create_sub_organization_modal_controller', function(){
    // globals set up and used in each test scenario
    var mock_organization_service, scope, controller, modal_state;
    var ctrl, ctrl_scope, modalInstance, timeout;
    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(function($controller, $rootScope, $uibModal, $q, organization_service, $timeout) {
        ctrl = $controller;
        scope = $rootScope;
        ctrl_scope = $rootScope.$new();
        modal_state = '';
        timeout = $timeout;

        mock_organization_service = organization_service;
        spyOn(mock_organization_service, 'create_sub_org')
            .andCallFake(function(org, sub_org){
                // return $q.reject for error scenario
                return $q.when({status: 'success'});
            }
        );
    }));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_sub_organization_modal_controller(){
        ctrl = ctrl('create_sub_organization_modal_controller', {
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

    it('should call the organization service to add a new sub_org',
        function() {
        // arrange
        create_sub_organization_modal_controller();

        // act
        ctrl_scope.$digest();
        ctrl_scope.sub_org.name = 'my shiny new org';
        ctrl_scope.sub_org.email = 'jb.smooth@be.com';
        ctrl_scope.submit_form(true);

        // assertions
        expect(mock_organization_service.create_sub_org)
            .toHaveBeenCalledWith(
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
