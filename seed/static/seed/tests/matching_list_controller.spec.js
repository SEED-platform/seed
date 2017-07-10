/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('Controller: matching_list_controller', function () {
  // globals set up and used in each test scenario
  var mock_matching_services, mock_inventory_services, scope, controller, delete_called;
  var matching_list_controller, matching_list_controller_scope, modalInstance, labels;
  var mock_spinner_utility;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(function ($controller, $rootScope, $uibModal, urls, $q, matching_service, inventory_service, spinner_utility) {
    controller = $controller;
    scope = $rootScope;
    matching_list_controller_scope = $rootScope.$new();
    matching_list_controller_scope.inventory_type = 'properties';

    mock_matching_services = matching_service;
    mock_inventory_services = inventory_service;
    spyOn(mock_inventory_services, 'get_matching_status')
        .andCallFake(function (import_file) {
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

    mock_spinner_utility = spinner_utility;
    spyOn(mock_spinner_utility, 'show')
        .andCallFake(function () {
          // Do nothing
        });
    spyOn(mock_spinner_utility, 'hide')
        .andCallFake(function () {
          // Do nothing
        });
  }));

  // this is outside the beforeEach so it can be configured by each unit test
  function create_dataset_detail_controller () {
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
    matching_list_controller = controller('matching_list_controller', {
      $scope: matching_list_controller_scope,
      inventory_payload: inventory_payload,
      $stateParams: {
        cycle_id: 2017,
        inventory_id: 4,
        inventory_type: 'properties',
        project_id: 2,
        import_file_id: 1
      },
      columns: [{
        name: 'pm_property_id',
        displayName: 'PM Property ID',
        type: 'number'
      }],
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


  /**
   * Test scenarios
   */

  it('should have a buildings payload with potential matches', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_list_controller_scope.$digest();
    var b = matching_list_controller_scope.inventory[0];

    // assertions
    expect(matching_list_controller_scope.inventory.length).toBe(1);
    expect(b.coparent.children).toEqual(b.children);
  });

  it('should provide to the view scope variables representing the number matched and the number of unmatched buildings', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_list_controller_scope.$digest();
    matching_list_controller_scope.update_number_matched();

    // assertions
    expect(matching_list_controller_scope.matched_buildings).toEqual(10);
    expect(matching_list_controller_scope.unmatched_buildings).toEqual(5);
    expect(mock_inventory_services.get_matching_status).toHaveBeenCalled();
  });

  it('should jump back to the matching list when the \'Back to list\' button is clicked', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_list_controller_scope.$digest();
    matching_list_controller_scope.fileChanged();

    // assertions
    expect($state.href('matching_list', { importfile_id: 3, inventory_type: 'taxlots' })).toBe('#/data/matching/3/taxlots');
  });

  it('should present an initial state with the matching buildings table',
    function () {
      // arrange
      create_dataset_detail_controller();

      // act
      matching_list_controller_scope.$digest();

      // assertions
      expect(matching_list_controller_scope.columns).toEqual([{name: 'pm_property_id', displayName: 'PM Property ID', type: 'number'}]);
      expect(matching_list_controller_scope.number_properties_matching_search).toEqual(1);
      expect(matching_list_controller_scope.number_properties_returned).toEqual(1);
      expect(matching_list_controller_scope.num_pages).toEqual(1);
      expect(mock_inventory_services.get_matching_status).toHaveBeenCalled();
    });
});
