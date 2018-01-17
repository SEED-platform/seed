/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
describe('Controller: matching_detail_controller', function () {
  // globals set up and used in each test scenario
  var mock_matching_service, mock_inventory_service, controller;
  var matching_detail_controller_scope;
  var mock_spinner_utility;


  // make the seed app available for each test
  // 'config.seed' is created in TestFilters.html
  beforeEach(function () {
    module('BE.seed');
    inject(function (_$httpBackend_) {
      $httpBackend = _$httpBackend_;
      $httpBackend.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(function ($controller, $rootScope, $uibModal, urls, $q, matching_service, inventory_service, spinner_utility) {
      controller = $controller;
      matching_detail_controller_scope = $rootScope.$new();
      matching_detail_controller_scope.inventory_type = 'properties';

      mock_matching_service = matching_service;
      mock_inventory_service = inventory_service;
      spyOn(mock_matching_service, 'match')
        .andCallFake(function () {
          return $q.resolve({
            status: 'success',
            child_id: 3
          });
        });
      spyOn(mock_matching_service, 'unmatch')
        .andCallFake(function () {
          return $q.resolve({
            status: 'success',
            child_id: 3
          });
        });
      spyOn(mock_matching_service, 'available_matches')
        .andCallFake(function () {
          return $q.resolve({
            status: 'success',
            states: [{
              extra_data: {},
              id: 3489754,
              lot_number: '239847190487'
            }]
          });
        });
      spyOn(mock_inventory_service, 'search_matching_inventory')
        .andCallFake(function () {
          if (!matching_detail_controller_scope.state.matched) {
            return $q.resolve({
              status: 'success',
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
          } else {
            return $q.resolve({
              status: 'success',
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
    });
  });

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
    controller('matching_detail_controller', {
      $scope: matching_detail_controller_scope,
      inventory_payload: inventory_payload,
      $stateParams: {
        cycle_id: 2017,
        inventory_id: 4,
        inventory_type: 'properties',
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
    console.dir(matching_detail_controller_scope);
    console.dir(mock_inventory_service);
    expect(mock_matching_service.match).toHaveBeenCalled();
    expect(mock_inventory_service.search_matching_inventory).toHaveBeenCalledWith(
      matching_detail_controller_scope.import_file.id, {
        get_coparents: true,
        inventory_type: 'properties',
        state_id: 345
      }
    );
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
    expect(mock_matching_service.unmatch).toHaveBeenCalled();
    expect(mock_inventory_service.search_matching_inventory).toHaveBeenCalledWith(
      matching_detail_controller_scope.import_file.id, {
        get_coparents: true,
        inventory_type: 'properties',
        state_id: 345
      });
    expect(matching_detail_controller_scope.state).toEqual({
      id: 76385,
      lot_number: '1552813',
      matched: false
    });
    expect(matching_detail_controller_scope.available_matches).toEqual([{
      extra_data: {},
      id: 3489754,
      lot_number: '239847190487'
    }]);
  });

  it('should exercise the inventory_service', function () {
    // arrange
    create_dataset_detail_controller();
    expect(function () {
      mock_inventory_service.get_property(null);
    }).toThrow(new Error('Invalid Parameter'));
    expect(function () {
      mock_inventory_service.update_property(null, null);
    }).toThrow(new Error('Invalid Parameter'));
    expect(function () {
      mock_inventory_service.update_property(0, null);
    }).toThrow(new Error('Invalid Parameter'));
    expect(function () {
      mock_inventory_service.get_taxlot(null);
    }).toThrow(new Error('Invalid Parameter'));
    expect(function () {
      mock_inventory_service.update_taxlot(null, null);
    }).toThrow(new Error('Invalid Parameter'));
    expect(function () {
      mock_inventory_service.update_taxlot(0, null);
    }).toThrow(new Error('Invalid Parameter'));
  });

});
