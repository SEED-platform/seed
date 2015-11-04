/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe("controller: building_detail_controller", function(){
    // globals set up and used in each test scenario
    var mockService, scope, controller, ngFilter, delete_called;
    var building_detail_ctrl, building_detail_ctrl_scope, modalInstance, labels;
    var mock_building_services, mock_project_service;
    var mock_building;

    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(
        function(
          $controller,
          $rootScope,
          $uibModal,
          urls,
          $q,
          building_services,
          project_service,
          $filter) {
            controller = $controller;
            scope = $rootScope;
            ngFilter = $filter;
            building_detail_ctrl_scope = $rootScope.$new();
            modal_state = "";
            delete_called = false;

            // mock the building_services factory methods used in the controller
            // and return their promises
            mock_building_services = building_services;
            mock_project_service = project_service;

            spyOn(mock_project_service, "get_project")
                .andCallFake(function(project_slug){
                    return $q.when(
                        {
                            "status": "success",
                            "project": {
                                id: 33,
                                name: "test project",
                                slug: project_slug
                            }
                        }
                    );
                }
            );
            spyOn(mock_project_service, "get_labels")
                .andCallFake(function(){
                    return $q.when(
                        {
                            "status": "success",
                            "labels": [{
                                id: 44,
                                name: "bad label",
                                color: "red"
                            }]
                        }
                    );
                }
            );
            spyOn(mock_project_service, "update_project_building")
                .andCallFake(function(building_id, project, label){
                    return $q.when(
                        {
                            "status": "success",
                            "approver": "bob doe",
                            "approved_date": "01/01/2012"
                        }
                    );
                }
            );
            spyOn(mock_building_services, "update_building")
                .andCallFake(function (building, org_id){
                    mock_building = building;
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
    function create_building_detail_controller(){
        var fake_building = {
            id: 511,
            pk: 511,
            gross_floor_area: 123456,
            gross_floor_area_source: 2,
            city: "DC",
            city_source: 4,
            tax_lot_id: "11/22",
            tax_lot_id_source: 3,
            extra_data: {
                'some other key': 12344,
                'some other key that is not in a parent': 223
            },
            extra_data_sources: {
                'some other key': 2,
                'some other key that is not in a parent': 3
            },
            created: "at some point"
        };
        var fake_imported_buildings = [
            {
                id: 2,
                pk: 2,
                gross_floor_area: 123456,
                gross_floor_area_source: null,
                city: "Washington, DC",
                city_source: null,
                extra_data: {
                    'some other key': 123,
                    'some other key that is not in a child': 333,
                    'some floor area': 444
                },
                extra_data_sources: {
                    'some other key': null,
                    'some other key that is not in a child': 111,
                    'some floor area': 444
                },
                created: "test"
            },
            {
                id: 3,
                pk: 3,
                gross_floor_area: 2111111,
                gross_floor_area_source: null,
                city: "Washington",
                city_source: null,
                tax_lot_id: "11/22",
                tax_lot_id_source: null,
                extra_data: {
                    'make it four': 4
                },
                extra_data_sources: {
                    'make it four': null
                }
            },{
                id: 4,
                pk: 4,
                gross_floor_area: 2111111,
                gross_floor_area_source: null,
                city: "Washington",
                city_source: null,
                tax_lot_id: "11/22",
                tax_lot_id_source: null,
                extra_data: {
                    'make it four': 5
                },
                extra_data_sources: {
                    'make it four': null
                }
            }
        ];
        var fake_payload = {
            "status": "success",
            "building": fake_building,
            "imported_buildings": fake_imported_buildings,
            "projects": [],
            "user_org_id": 42
        };
        var fake_all_columns = [{
            "title": "PM Property ID",
            "sort_column": "pm_property_id",
            "class": "is_aligned_right",
            "title_class": "",
            "type": "link",
            "field_type": "building_information",
            "sortable": true,
            "checked": false,
            "static": false,
            "link": true
        },
        {
            "title": "Tax Lot ID",
            "sort_column": "tax_lot_id",
            "class": "is_aligned_right",
            "title_class": "",
            "type": "link",
            "field_type": "building_information",
            "sortable": true,
            "checked": false,
            "static": false,
            "link": true
        },
        {
            "title": "Custom ID 1",
            "sort_column": "custom_id_1",
            "class": "is_aligned_right whitespace",
            "title_class": "",
            "type": "link",
            "field_type": "building_information",
            "sortable": true,
            "checked": false,
            "static": false,
            "link": true
        },
        {
            "title": "Property Name",
            "sort_column": "property_name",
            "class": "",
            "title_class": "",
            "type": "string",
            "field_type": "building_information",
            "sortable": true,
            "checked": false
        }];
        building_detail_ctrl = controller('building_detail_controller', {
            $scope: building_detail_ctrl_scope,
            $routeParams: {
                building_id: 1,
                project_id: 2
            },
            building_payload: fake_payload,
            all_columns: {
                fields: fake_all_columns
            },
            audit_payload: {
                audit_logs: []
            }
        });
    }

    /*
     * Test scenarios
     */

    it("should have an building payload", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(building_detail_ctrl_scope.building.id).toBe(511);
        expect(building_detail_ctrl_scope.imported_buildings[0].id).toBe(2);
    });

    it("should get labels on load", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(building_detail_ctrl_scope.labels[0].id).toBe(44);
        expect(building_detail_ctrl_scope.labels[0].name).toBe("bad label");
        expect(building_detail_ctrl_scope.labels[0].color).toBe("red");
    });

    it("should highlight the active project", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(building_detail_ctrl_scope.is_active_project({id:33}))
        .toBe(true);
        expect(building_detail_ctrl_scope.is_active_project({id:34}))
        .toBe(false);
        building_detail_ctrl_scope.project = undefined;
        expect(building_detail_ctrl_scope.is_active_project({id:34}))
        .toBe(false);
    });

    it("should make a copy of building while making edits", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.save_building_state();
        building_detail_ctrl_scope.building.gross_floor_area = 43214;

        // assertions
        expect(building_detail_ctrl_scope.building_copy.gross_floor_area)
        .toBe(123456);
    });
    it("should restore the copy of building if a user clicks cancel",
        function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.save_building_state();
        building_detail_ctrl_scope.building.gross_floor_area = 43214;
        building_detail_ctrl_scope.restore_building();

        // assertions
        expect(building_detail_ctrl_scope.building.gross_floor_area)
        .toBe(123456);
        expect(building_detail_ctrl_scope.building.edit_form_showing).toBe(false);
    });
    it("should save a building when a user clicks the save button", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.building.gross_floor_area = 43214;
        building_detail_ctrl_scope.save_building();

        // assertions
        expect(mock_building_services.update_building)
        .toHaveBeenCalledWith(building_detail_ctrl_scope.building, 42);
        expect(mock_building.gross_floor_area).toEqual(43214);
    });
    it("should show a default label if a building doesn't have one", function() {
        // arrange
        create_building_detail_controller();
        var building_with_label = {
            label: {
                name: "hello",
                label: "success"
            }
        };
        var building_without_label = {};
        var label_with, label_without;

        // act
        building_detail_ctrl_scope.$digest();
        label_with = building_detail_ctrl_scope.get_label(building_with_label);
        label_without = building_detail_ctrl_scope.get_label(building_without_label);

        // assertions
        expect(label_with).toEqual({
                name: "hello",
                label: "success"
            });
        expect(label_without).toEqual({
                name: "Add Label",
                label: "default"
            });
    });

    it("should show a project or buildings breadcrumb", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.user.project_slug = "project_1";

        // assertions
        expect(building_detail_ctrl_scope.is_project()).toEqual(true);
        building_detail_ctrl_scope.user.project_slug = undefined;
        expect(building_detail_ctrl_scope.is_project()).toEqual(false);

    });
    it("should show the default projects table if a user has no compliance" +
        " projects", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(building_detail_ctrl_scope.user.has_projects()).toEqual(false);
        building_detail_ctrl_scope.projects = [{id: 1, name: "a"}];
        expect(building_detail_ctrl_scope.user.has_projects()).toEqual(true);

    });

    it("should set only building attribute to master, not ids or children", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(building_detail_ctrl_scope.is_valid_key('id')).toEqual(false);
        expect(building_detail_ctrl_scope.is_valid_key('pk')).toEqual(false);
        expect(building_detail_ctrl_scope.is_valid_key('pk_source')).toEqual(false);
        expect(building_detail_ctrl_scope.is_valid_key(' extra_data ')).toEqual(false);
        expect(building_detail_ctrl_scope.is_valid_key('gross_floor_area'))
          .toEqual(true);
    });
    it("should update a project-building label", function() {
        // arrange
        create_building_detail_controller();
        var project = {
            id: 2,
            building: {}
        };

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.update_project_building(project,
            {
                name: "label name",
                color: "red"
            });
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(mock_project_service.update_project_building).toHaveBeenCalled();
        expect(project.building.approver).toEqual("bob doe");
        expect(project.building.approved_date).toEqual("01/01/2012");
        expect(project.building.label.name).toEqual("label name");
        expect(project.building.label.color).toEqual("red");

    });
    it("should set a field as source when clicked", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.imported_buildings[0].is_master = true;
        expect(building_detail_ctrl_scope.building.gross_floor_area_source)
          .not.toEqual(building_detail_ctrl_scope.building.id);
        building_detail_ctrl_scope.set_self_as_source('gross_floor_area');
        building_detail_ctrl_scope.set_self_as_source('some other key', true);
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(building_detail_ctrl_scope.building.gross_floor_area_source)
          .toEqual(building_detail_ctrl_scope.building.id);
        expect(building_detail_ctrl_scope.imported_buildings[0].is_master)
          .toEqual(false);
    });
    it("should set a column as the dominant source when clicked", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.imported_buildings[1].is_master = true;
        building_detail_ctrl_scope.make_source_default(
            building_detail_ctrl_scope.imported_buildings[0]);
        building_detail_ctrl_scope.$digest();

        // assertions
        var b = building_detail_ctrl_scope.building,
            i = building_detail_ctrl_scope.imported_buildings[0],
            i_other = building_detail_ctrl_scope.imported_buildings[1];

        expect(b.gross_floor_area_source).toEqual(i.id);
        expect(b.id).not.toEqual(i.id);
        expect(b.pk).not.toEqual(i.id);
        expect(b.city).toEqual(i.city);
        expect(b.city_source).toEqual(i.id);
        expect(b.tax_lot_id).toEqual("11/22");
        expect(b.tax_lot_id_source).toEqual(i_other.id);
        expect(b.extra_data['some other key']).toEqual(123);
        expect(b.extra_data_sources['some other key']).toEqual(i.id);
        expect(b.extra_data['some other key that is not in a child']).toEqual(333);
        expect(b.extra_data_sources['some other key that is not in a child']).toEqual(i.id);
        expect(b.extra_data['some other key that is not in a parent']).toEqual(223);
        expect(b.extra_data_sources['some other key that is not in a parent']).toEqual(i_other.id);
        expect(b.created).toEqual("at some point");

        expect(i.is_master).toEqual(true);
        expect(i_other.is_master).toEqual(false);
    });
    it("should set the master building value when parent's value is clicked",
        function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.imported_buildings[1].is_master = true;
        building_detail_ctrl_scope.set_building_attribute(
            building_detail_ctrl_scope.imported_buildings[0], 'city');
        building_detail_ctrl_scope.set_building_attribute(
            building_detail_ctrl_scope.imported_buildings[0], 'some other key', true);
        building_detail_ctrl_scope.$digest();

        // assertions
        var b = building_detail_ctrl_scope.building,
            i = building_detail_ctrl_scope.imported_buildings[0],
            i_other = building_detail_ctrl_scope.imported_buildings[1];

        expect(b.id).not.toEqual(i.id);
        expect(b.pk).not.toEqual(i.id);
        expect(b.city).toEqual(i.city);
        expect(b.city_source).toEqual(i.id);
        expect(b.tax_lot_id).toEqual("11/22");
        expect(b.tax_lot_id_source).toEqual(i_other.id);
        expect(b.extra_data['some other key']).toEqual(123);
        expect(b.extra_data_sources['some other key']).toEqual(i.id);

        expect(i.is_master).toEqual(false);
        expect(i_other.is_master).toEqual(false);
    });

    it("should display all the data within all the buildings", function() {
        // arrange
        create_building_detail_controller();
        var keys;

        // act
        building_detail_ctrl_scope.$digest();

        // assertions
        var edc = building_detail_ctrl_scope.data_columns;

        // should not duplicate keys
        expect(edc.length).toEqual(8);
        keys = edc.map(function ( d ) {
            return d.key;
        });
        expect(keys.indexOf('make it four')).toEqual(4);
    });

    it("should display Floor Areas", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();
        building_detail_ctrl_scope.$digest();

        // assertions
        var area_fields = building_detail_ctrl_scope.floor_area_fields;
        expect(area_fields.length).toEqual(1);
    });

    it("should display Floor Areas with number", function() {
        // arrange
        create_building_detail_controller();

        // act
        building_detail_ctrl_scope.$digest();

        // assertions
        expect(building_detail_ctrl_scope.get_number("")).toEqual(0);
        expect(building_detail_ctrl_scope.get_number("123,123,123")).toEqual(123123123);
        expect(building_detail_ctrl_scope.get_number("123,123,123.123")).toEqual(123123123.123);
        expect(building_detail_ctrl_scope.get_number("-123,123,123")).toEqual(-123123123);
        expect(building_detail_ctrl_scope.get_number(-123123123)).toEqual(-123123123);


    });
});
