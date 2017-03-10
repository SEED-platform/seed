/**
 * :copyright: (c) 2014 Building Energy Inc
 */
describe('Controller: matching_controller', function () {
  // globals set up and used in each test scenario
  var mock_matching_services, mock_inventory_services, mock_building_services, scope, controller, delete_called;
  var matching_controller, matching_controller_scope, modalInstance, labels;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(function ($controller, $rootScope, $uibModal, urls, $q, matching_service, inventory_service, building_services) {
    controller = $controller;
    scope = $rootScope;
    matching_controller_scope = $rootScope.$new();
    matching_controller_scope.inventory_type = 'properties';

    mock_matching_services = matching_service;
    mock_building_services = building_services;
    mock_inventory_services = inventory_service;
    spyOn(mock_building_services, 'get_matching_results')
        .andCallFake(function(import_file){
            // return $q.reject for error scenario
            return $q.when({
              properties: {
                status: 'success',
                matched: 10,
                unmatched: 5,
                duplicates: 0
              }
            });
        });
    spyOn(mock_inventory_services, 'save_property_match')
      .andCallFake(function (b1, b2, create) {
          return $q.when({
            status: 'success',
            child_id: 3
          });
        });
    spyOn(mock_inventory_services, 'search_matching_inventory')
      .andCallFake(function (q, number_per_page, current_page, order_by, sort_reverse,
                             filter_params, file_id) {
        var bldgs;
        if (filter_params.children__isnull === undefined) {
          bldgs = [{
            pm_property_id: 1
          }, {
            pm_property_id: 2
          }, {
            pm_property_id: 3
          }];
        } else if (filter_params.children__isnull === false) {
          bldgs = [{
            pm_property_id: 1
          }];
        } else if (filter_params.children__isnull === true) {
          bldgs = [{
            pm_property_id: 2
          }, {
            pm_property_id: 3
          }];
        }

        return $q.when({
          status: 'success',
          number_properties_returned: bldgs.length,
          number_properties_matching_search: bldgs.length,
          properties: bldgs
        });

      });
  }));

  // this is outside the beforeEach so it can be configured by each unit test
  function create_dataset_detail_controller() {
    var inventory_payload = {
      properties: [
        {
          pm_property_id: 1,
          tax_lot_id: null,
          custom_id_1: 2,
          gross_floor_area: 111,
          matched: true,
          id: 1,
          children: [3],
          coparent: {
            pm_property_id: null,
            tax_lot_id: 2,
            custom_id_1: null,
            gross_floor_area: 111,
            id: 2,
            children: [3]
          }
        }
      ],
      number_properties_matching_search: 1,
      number_properties_returned: 1
    };
    matching_controller = controller('matching_controller', {
      $scope: matching_controller_scope,
      inventory_payload: inventory_payload,
      $stateParams: {
          cycle_id: 2017,
          inventory_id: 4,
          inventory_type: 'properties',
          project_id: 2,
          import_file_id: 1
      },
      all_columns: {
        fields: [{sort_column: 'pm_property_id'}]
      },
      default_columns: {
        columns: ['pm_property_id']
      },
      cycles: {
        cycles: [{
          end: '2016-01-01T07:00:00Z',
          name: '2015',
          start: '2015-01-01T07:00:00Z',
          user: null,
          id: 1
        }]
      },
      import_file_payload: {
        import_file: {
          id: 1,
          cycle: 1,
          dataset: {
            importfiles: [{
              id: 1,
              name: 'file_1.csv',
              mapping_done: true,
              cycle: 1
            }, {
              id: 2,
              name: 'file_2.csv',
              mapping_done: true,
              cycle: 1
            }]
          }
        }
      }
    });
  }


  /*
   * Test scenarios
   */

  it('should have a buildings payload with potential matches', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_controller_scope.$digest();
    var b = matching_controller_scope.inventory[0];

    // assertions
    expect(matching_controller_scope.inventory.length).toBe(1);
    expect(b.coparent.children).toEqual(b.children);
  });

  it('should provide to the view scope variables representing the number matched and the number of unmatched buildings', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_controller_scope.$digest();
    matching_controller_scope.update_number_matched();

    // assertions
    expect(matching_controller_scope.matched_buildings).toEqual(10);
    expect(matching_controller_scope.unmatched_buildings).toEqual(5);
    expect(mock_building_services.get_matching_results).toHaveBeenCalled();
  });

  it('should jump back to the matching list when the \'Back to list\' button is clicked', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_controller_scope.$digest();
    matching_controller_scope.show_building_list = false;
    matching_controller_scope.back_to_list();

    // assertions
    expect(matching_controller_scope.show_building_list).toEqual(true);
  });

  it('should present an initial state with the matching buildings table',
    function () {
      // arrange
      create_dataset_detail_controller();

      // act
      matching_controller_scope.$digest();

      // assertions
      expect(matching_controller_scope.columns).toEqual([{sort_column: 'pm_property_id'}]);
      expect(matching_controller_scope.number_properties_matching_search).toEqual(1);
      expect(matching_controller_scope.number_properties_returned).toEqual(1);
      expect(matching_controller_scope.num_pages).toEqual(1);
      expect(mock_building_services.get_matching_results).toHaveBeenCalled();
    });
  it('should match a building in the matching list', function () {
    // arrange
    create_dataset_detail_controller();
    var b1, b2;
    b2 = {
      id: 2,
      children: [],
      matched: false
    };
    b1 = {
      id: 1,
      children: [],
      matched: true,
      coparent: b2
    };

    // act
    matching_controller_scope.$digest();
    matching_controller_scope.toggle_match(b1);
    matching_controller_scope.$digest();

    // assertions
    expect(mock_inventory_services.save_property_match).toHaveBeenCalledWith(b1.id, b2.id, true);
    expect(mock_building_services.get_matching_results).toHaveBeenCalled();
    expect(b1.children[0]).toEqual(3);
  });
  it('Should update the list of buildings correctly when \'Show Matched\' is selected', function () {
    //arrange
    create_dataset_detail_controller();

    //act
    matching_controller_scope.update_show_filter('Show Matched'); //DMcQ: This really should be a ref to the 'constant' defined in the controller, but not sure how to do that yet...
    matching_controller_scope.$digest();

    //assertions
    expect(mock_inventory_services.search_matching_inventory).toHaveBeenCalled();
    expect(matching_controller_scope.inventory.length).toEqual(1);
    expect(matching_controller_scope.number_properties_returned).toEqual(1);
  });
  it('Should update the list of buildings correctly when \'Show Unmatched\' is selected', function () {
    //arrange
    create_dataset_detail_controller();

    //act
    matching_controller_scope.update_show_filter('Show Unmatched'); //DMcQ: This really should be a ref to the 'constant' defined in the controller, but not sure how to do that yet...
    matching_controller_scope.$digest();

    //assertions
    expect(mock_inventory_services.search_matching_inventory).toHaveBeenCalled();
    expect(matching_controller_scope.inventory.length).toEqual(2);
    expect(matching_controller_scope.number_properties_returned).toEqual(2);
  });
  it('Should update the list of buildings correctly when \'Show All\' is selected', function () {
    //arrange
    create_dataset_detail_controller();

    //act
    matching_controller_scope.update_show_filter('Show All'); //DMcQ: This really should be a ref to the 'constant' defined in the controller, but not sure how to do that yet...
    matching_controller_scope.$digest();

    //assertions
    expect(mock_inventory_services.search_matching_inventory).toHaveBeenCalled();
    expect(matching_controller_scope.inventory.length).toEqual(3);
    expect(matching_controller_scope.number_properties_returned).toEqual(3);
  });


});
