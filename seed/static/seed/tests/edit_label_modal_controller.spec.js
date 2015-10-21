/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe("controller: edit_label_modal_ctrl", function(){
    // globals set up and used in each test scenario
    var mockService, scope, controller, modal_state;
    var edit_ctrl, edit_ctrl_scope, modalInstance, labels;
    var deleted_label, updated_label;
    var return_labels = [
        {
            "name": 'compliant',
            "color": 'green',
            "id": 1
        },
        {
            "name": "new label",
            "color": "blue",
            "id": 2
        }
    ];

    // make the seed app available for each test
    // 'config.seed' is created in TestFilters.html
    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(function($controller, $rootScope, $uibModal, urls, $q, project_service) {
        controller = $controller;
        scope = $rootScope;
        edit_ctrl_scope = $rootScope.$new();
        modal_state = "";

        // mock the project_service factory methods used in the controller
        // and return their promises
        mock_project_service = project_service;
        spyOn(mock_project_service, "get_labels")
            .andCallFake(function(){
                // return $q.reject for error scenario
                return $q.when({"status": "success", "labels": return_labels});
            }
        );
        spyOn(mock_project_service, "add_label")
            .andCallFake(function(){
                // return $q.reject for error scenario
                return $q.when({"status": "success"});
            }
        );
        spyOn(mock_project_service, "delete_label")
            .andCallFake(function(label){
                deleted_label = label;
                // return $q.reject for error scenario
                return $q.when({"status": "success"});
            }
        );
        spyOn(mock_project_service, "update_label")
            .andCallFake(function(label){
                updated_label = label;
                // return $q.reject for error scenario
                return $q.when({"status": "success"});
            }
        );

    }));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_edit_modal_controller(){
        var labels = [
            {
                "name": 'compliant',
                "color": 'green',
                "id": 1
            }
        ];

        edit_ctrl = controller('edit_label_modal_ctrl', {
            $scope: edit_ctrl_scope,
            $modalInstance: {
                close: function() {
                    modal_state = "close";
                },
                dismiss: function() {
                    modal_state = "dismiss";
                }
            },
            labels: labels
        });
    }

    /*
     * Test scenarios
     */

    it("should initialize the default label", function() {
        // arrange
        create_edit_modal_controller();

        // act
        edit_ctrl_scope.$digest();
        edit_ctrl_scope.initialize_label_modal();

        // assertions
        expect(edit_ctrl_scope.label_modal.color).toBe("gray");
        expect(edit_ctrl_scope.label_modal.label).toBe("default");
        expect(edit_ctrl_scope.label_modal.name).toBe("");
        expect(edit_ctrl_scope.modal.label.state).toBe("create");
    });

    it("should get the labels available to an organization", function() {
        // arrange
        create_edit_modal_controller();

        // act
        edit_ctrl_scope.add_label({});  // calls private get_labels
        edit_ctrl_scope.$digest();

        // assertions
        expect(edit_ctrl_scope.labels.length).toBe(2);
    });

    it("should add a label in the user's organization", function() {
        // arrange
        create_edit_modal_controller();
        var label_to_add = {
            color: "blue",
            label: "primary",
            name: "new label"
        };

        // act
        edit_ctrl_scope.add_label(label_to_add);
        edit_ctrl_scope.$digest();

        // assertions
        expect(edit_ctrl_scope.labels.length).toBe(2);
        expect(edit_ctrl_scope.labels[1].color).toBe("blue");
        expect(edit_ctrl_scope.labels[1].name).toBe("new label");
    });

    it("should close the modal when the close funtion is called", function() {
        // arrange
        create_edit_modal_controller();

        // act
        edit_ctrl_scope.close();
        edit_ctrl_scope.$digest();

        // assertions
        expect(modal_state).toBe("close");
    });

    it("should cancel the modal when the cancel funtion is called", function() {
        // arrange
        create_edit_modal_controller();

        // act
        edit_ctrl_scope.cancel();
        edit_ctrl_scope.$digest();

        // assertions
        expect(modal_state).toBe("dismiss");
    });

    it("sets the label_modal to the label when its edit button is clicked", function() {
        // arrange
        create_edit_modal_controller();
        var label = edit_ctrl_scope.labels[0];

        // act
        edit_ctrl_scope.edit_label(label);
        edit_ctrl_scope.$digest();

        // assertions
        expect(edit_ctrl_scope.label_modal.color).toBe(label.color);
        expect(edit_ctrl_scope.label_modal.name).toBe(label.name);
        expect(edit_ctrl_scope.modal.label.state).toBe("edit");

        // assert that edit_ctrl_scope.label_modal is a copy and not a reference to label
        edit_ctrl_scope.label_modal.name = "random name here";
        expect(edit_ctrl_scope.label_modal.name).not.toBe(label.name);
    });
    
    it("deletes the appropriate label when the delete button is clicked", function() {
        // arrange
        create_edit_modal_controller();
        var label = edit_ctrl_scope.labels[0];

        // act
        edit_ctrl_scope.delete_label(label);
        edit_ctrl_scope.$digest();

        // assertions
        expect(deleted_label).toBe(label);
    });

    it("updates the appropriate label when the update label button is clicked", function() {
        // arrange
        create_edit_modal_controller();
        var label = edit_ctrl_scope.labels[0];

        // act
        edit_ctrl_scope.edit_label(label);
        edit_ctrl_scope.$digest();
        edit_ctrl_scope.label_modal.name = "harry";
        edit_ctrl_scope.label_modal.color = "blue";
        edit_ctrl_scope.update_label(edit_ctrl_scope.label_modal);
        edit_ctrl_scope.$digest();

        // assertions
        expect(mock_project_service.update_label).toHaveBeenCalledWith(edit_ctrl_scope.label_modal);
        expect(updated_label).toBe(edit_ctrl_scope.label_modal);
    });

});
