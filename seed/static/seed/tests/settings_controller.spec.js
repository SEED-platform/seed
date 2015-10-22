/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe("controller: settings_controller", function(){
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
            
        }
    ));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_settings_controller(){
        ctrl = ctrl('settings_controller', {
            $scope: ctrl_scope,
            all_columns: {fields: [
                {checked: false, title: 'PM Property ID', sort_column: 'pm_property_id'},
                {checked: false, title: 'G', sort_column: 'g'},
                {checked: false, title: "Gross Floor Area", sort_column: 'gross_floor_area'}
            ]},
            organization_payload: {
                organization: {name: 'my org', id: 4}
            },
            query_threshold_payload: {
                query_threshold: 10
            },
            shared_fields_payload: {
                shared_fields: [
                    {
                        title: "PM Property Id",
                        sort_column: "pm_property_id"
                    }
                ],
                public_fields: [
                {
                    title: "Gross Floor Area",
                    sort_column: "gross_floor_area"
                }]
            },
            auth_payload: {
                auth: {
                    'is_owner': true,
                    'is_parent_org_owner': false
                }
            }
        });
    }

    /*
     * Test scenarios
     */

    it("should accepts its payload", function() {
        // arrange
        create_settings_controller();

        // act
        ctrl_scope.$digest();

        // assertions
        expect(ctrl_scope.org).toEqual({
            name : 'my org',
            id : 4,
            query_threshold: 10
        });
        expect(ctrl_scope.fields[0].checked).toEqual(true);
        expect(ctrl_scope.fields[1].checked).toEqual(false);
        expect(ctrl_scope.fields[0].title).toEqual('PM Property ID');
    });
    it("should select all", function() {
        // arrange
        create_settings_controller();

        // act
        ctrl_scope.$digest();
        ctrl_scope.controls.select_all = true;
        ctrl_scope.select_all_clicked();
        ctrl_scope.$digest();

        // assertions
        expect(ctrl_scope.infinite_fields[0].checked).toEqual(true);
    });
});
