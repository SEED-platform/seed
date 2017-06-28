/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('Controller: matching_detail_controller', function () {
  // globals set up and used in each test scenario
  var mock_matching_services, mock_inventory_services, scope, controller, delete_called;
  var matching_detail_controller, matching_detail_controller_scope, modalInstance, labels;
  var mock_spinner_utility, mock_state_payload;
  var first = true;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
  });

  // inject AngularJS dependencies for the controller
  beforeEach(inject(function ($controller, $rootScope, $uibModal, urls, $q, matching_service, inventory_service, spinner_utility) {
    controller = $controller;
    scope = $rootScope;
    matching_detail_controller_scope = $rootScope.$new();
    matching_detail_controller_scope.inventory_type = 'properties';

    mock_matching_services = matching_service;
    mock_inventory_services = inventory_service;
    spyOn(mock_matching_services, 'match')
      .andCallFake(function () {
        return $q.when({
          status: 'success',
          child_id: 3
        });
      });
    spyOn(mock_matching_services, 'unmatch')
      .andCallFake(function () {
        return $q.when({
          status: 'success',
          child_id: 3
        });
      });
    spyOn(mock_matching_services, 'available_matches')
      .andCallFake(function (importfile_id, inventory_type, state_id) {
        return $q.when({
          status: 'success',
          states: [{
            extra_data: {},
            id: 3489754,
            lot_number: '239847190487'
          }]
        });
      });
    spyOn(mock_inventory_services, 'search_matching_inventory')
      .andCallFake(function (file_id, options) {
        var bldgs;
        if (!matching_detail_controller_scope.state.matched) {
          return $q.when({
            status: 'success',
            // number_properties_returned: bldgs.length,
            // number_properties_matching_search: bldgs.length,
            // properties: bldgs,
            state: {
              coparent: {
                extra_data: {},
                lot_number: '11160509',
                id: 76386
              },
              id: 76385,
              lot_number: '1552813',
              matched: true
            }
          });
          first = false;
        } else {
          return $q.when({
            status: 'success',
            // number_properties_returned: bldgs.length,
            // number_properties_matching_search: bldgs.length,
            // properties: bldgs,
            state: {
              id: 76385,
              lot_number: '1552813',
              matched: false
            }
          });
        }

      });

    mock_spinner_utility = spinner_utility;

    spyOn(mock_spinner_utility, 'show')
      .andCallFake(function () {
        //do nothing
      });
    spyOn(mock_spinner_utility, 'hide')
      .andCallFake(function () {
        //do nothing
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
    var state_payload = {
      state: {
        matched: false
      }
    };
    var available_matches = {
      states: [{
        id: 'fake'
      }]
    };
    matching_detail_controller = controller('matching_detail_controller', {
      $scope: matching_detail_controller_scope,
      inventory_payload: inventory_payload,
      $stateParams: {
        cycle_id: 2017,
        inventory_id: 4,
        inventory_type: 'properties',
        project_id: 2,
        import_file_id: 1,
        state_id: 345,
        importfile_id: 999999
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
      state_payload: state_payload,
      available_matches: available_matches,
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

  it('should match and then unmatch a building in the matching list', function () {
    // arrange
    create_dataset_detail_controller();

    // act
    matching_detail_controller_scope.$digest();
    matching_detail_controller_scope.match({state: {id: 1234}});
    matching_detail_controller_scope.$digest();

    // assertions
    expect(mock_matching_services.match).toHaveBeenCalled();
    expect(mock_inventory_services.search_matching_inventory).toHaveBeenCalledWith(matching_detail_controller_scope.importfile_id,
      {get_coparents: true, inventory_type: 'properties', state_id: 345});
    expect(matching_detail_controller_scope.state).toEqual({
      coparent: {extra_data: {}, lot_number: '11160509', id: 76386},
      id: 76385, lot_number: '1552813', matched: true
    });
    expect(matching_detail_controller_scope.available_matches).toEqual([{
      extra_data: {},
      id: 3489754,
      lot_number: '239847190487'
    }]);

    // act
    matching_detail_controller_scope.$digest();
    matching_detail_controller_scope.unmatch();
    matching_detail_controller_scope.$digest();

    // assertions
    expect(mock_matching_services.unmatch).toHaveBeenCalled();
    expect(mock_inventory_services.search_matching_inventory).toHaveBeenCalledWith(matching_detail_controller_scope.importfile_id,
      {get_coparents: true, inventory_type: 'properties', state_id: 345});
    expect(matching_detail_controller_scope.state).toEqual({id: 76385, lot_number: '1552813', matched: false});
    expect(matching_detail_controller_scope.available_matches).toEqual([{
      extra_data: {},
      id: 3489754,
      lot_number: '239847190487'
    }]);
  });

  it('should exercise the inventory_service', function () {
    // arrange
    create_dataset_detail_controller();
    expect( function(){ mock_inventory_services.get_property(null, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.get_property(0, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.update_property(null, null, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.update_property(0, null, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.update_property(0, 0, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.get_taxlot(null, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.get_taxlot(0, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.update_taxlot(null, null, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.update_taxlot(0, null, null); } ).toThrow(new Error("Invalid Parameter"));
    expect( function(){ mock_inventory_services.update_taxlot(0, 0, null); } ).toThrow(new Error("Invalid Parameter"));
  });

});
