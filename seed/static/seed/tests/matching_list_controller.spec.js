/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('Controller: matching_list_controller', function () {
  // globals set up and used in each test scenario
  var mock_inventory_service, controller, $state;
  var matching_list_controller_scope;
  var mock_spinner_utility;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $q, _$state_, inventory_service, spinner_utility) {
      controller = $controller;
      $state = _$state_;
      matching_list_controller_scope = $rootScope.$new();
      matching_list_controller_scope.inventory_type = 'properties';

      mock_inventory_service = inventory_service;
      spyOn(mock_inventory_service, 'get_matching_status')
        .andCallFake(function () {
          // return $q.reject for error scenario
          return $q.resolve({
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
    });
  });

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
    controller('matching_list_controller', {
      $scope: matching_list_controller_scope,
      inventory_payload: inventory_payload,
      $stateParams: {
        cycle_id: 2017,
        inventory_id: 4,
        inventory_type: 'properties',
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
    expect(matching_list_controller_scope.matched_buildings).toEqual(1);
    expect(matching_list_controller_scope.unmatched_buildings).toEqual(0);
    expect(mock_inventory_service.get_matching_status).toHaveBeenCalled();
  });

  it('should jump back to the matching list when the "Back to list" button is clicked', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_list_controller_scope.$digest();
    matching_list_controller_scope.fileChanged();

    // assertions
    expect($state.href('matching_list', {
      importfile_id: 3,
      inventory_type: 'taxlots'
    })).toBe('#/data/matching/3/taxlots');
  });

  it('should present an initial state with the matching buildings table', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_list_controller_scope.$digest();

    // assertions
    expect(matching_list_controller_scope.leftColumns).toEqual([{
      name: 'pm_property_id',
      displayName: 'PM Property ID',
      type: 'number'
    }]);
    expect(matching_list_controller_scope.matched_buildings).toEqual(1);
    expect(matching_list_controller_scope.number_of_pages).toEqual(1);
  });
});
