/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe('controller: admin_controller', function(){
    var mock_organization_service;

    beforeEach(function() {
        module('BE.seed');
    });
    beforeEach(inject(function($controller, $rootScope, user_service, organization_service, $q) {
        this.scope = $rootScope.$new();
        $controller('admin_controller', {
            $scope: this.scope,
            user_service: user_service,
            organization_service: organization_service,
            user_profile_payload: {
              user: {first_name: 'b', last_name: 'd'}
            }
        });
    }));
    describe('update_alert', function() {
        it('should set the show state to true', function() {
            // arrange

            // act
            this.scope.update_alert(true, 'test message');

            // assertions
            expect(this.scope.alert.show).toBe(true);
            expect(this.scope.alert.message).toBe('test message');
        });
    });

    it('should raise an confirm window when the delete buildings button is clicked', function() {
        // arrange
        var oldConfirm = confirm;
        confirm = jasmine.createSpy();

        // act
        this.scope.confirm_inventory_delete({org_id: 44, name: 'my new org'});

        // assertions
        expect(confirm).toHaveBeenCalledWith(
            'Are you sure you want to PERMANENTLY delete \'' +
            'my new org' + '\'s properties and tax lots?');

        confirm = oldConfirm;
    });
});
