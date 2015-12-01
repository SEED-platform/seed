describe("controller: update_building_labels_modal_ctrl", function(){
    // globals set up and used in each test scenario
    var mockService, scope, controller, modal_state, mock_notification, mock_search;
    var update_ctrl, update_ctrl_scope, modalInstance, labels;
    
    var return_obj_for_create_label = {
        "color":"gray",
        "is_applied":true,
        "id":100,
        "name":"new label 1",
        "label":"default",
        "text":"new label 1"
    };

    var available_colors  = [
        {
            'label': 'success',
            'color': 'green'
        },
        {
            'label': 'danger',
            'color': 'red'
        },
    ];

                   

    // make the seed app available for each test
    // 'config.seed' is created in TestFilters.html
    beforeEach(function() {
        module('BE.seed');
    });

    // inject AngularJS dependencies for the controller
    beforeEach(inject(function($controller, $rootScope, $uibModal, $q, label_service, notification) {

        controller = $controller;
        scope = $rootScope;
        update_ctrl_scope = $rootScope.$new();

        // mock the label_service factory methods used in the controller
        // and return their promises (if necessary).
        mock_label_service = label_service;
        spyOn(mock_label_service, "create_label")
            .andCallFake(function(){
                // return $q.reject for error scenario
                return $q.when({"status": "success", "label": return_obj_for_create_label});
            }
        );
        spyOn(mock_label_service, "update_building_labels")
            .andCallFake(function(){
                // return $q.reject for error scenario
                return $q.when({"status": "success"});
            }
        );     
        spyOn(mock_label_service, "get_available_colors")
            .andCallFake(function(){
                return available_colors;
            }
        );    

        //mock the notification service
        mock_notification = notification;
        spyOn(mock_notification, "primary")
            .andCallFake(function(){
                //do nothing
            }
        );  



    }));

    // this is outside the beforeEach so it can be configured by each unit test
    function create_update_building_labels_modal_ctrl(){
       

        // We only need to mock three properties of the search object for this controller 
        var mock_search = {
            "selected_buildings": [2594,2777],
            "select_all_checkbox" : false,
            "filter_params" : {}
        };

        // These labels are 
        var supplied_labels = [
            {   "color":"gray",
                "is_applied":true,
                "id":71,
                "name":"test label 1",
                "label":"default",
                "text":"test label 1",
            },
            {   "color":"green",
                "is_applied":false,
                "id":69,
                "name":"test label 2",
                "label":"success",
                "text":"test label 2",
            }
        ];

        //function ($scope, $uibModalInstance, label_service, search, notification) {
        update_ctrl = controller('update_building_labels_modal_ctrl', {
            $scope: edit_ctrl_scope,
            $uibModalInstance: {
                close: function() {
                    modal_state = "close";
                },
                dismiss: function() {
                    modal_state = "dismiss";
                }
            },
            label_service: mock_label_service,
            search: mock_search,
            notification: mock_notification
        });
    }

    /*
     * Test scenarios
     */

    it("should initialize the default 'new' label", function() {
        
        // arrange
        create_update_building_labels_modal_ctrl();

        // act
        update_ctrl_scope.$digest();
        update_ctrl_scope.initialize_label_modal();

        // assertions
        expect(update_ctrl_scope.new_label.color).toBe("gray");
        expect(update_ctrl_scope.new_label.label).toBe("default");
        expect(update_ctrl_scope.new_label.name).toBe("");
    });


});
