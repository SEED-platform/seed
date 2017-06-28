// /**
//  * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
//  * :author
//  */
// describe('controller: export_modal_controller', function () {
//   // globals set up and used in each test scenario
//   var mock_export_service, scope, controller, modal_state;
//   var ctrl, ctrl_scope, modalInstance, timeout;
//   // make the seed app available for each test
//   // 'config.seed' is created in TestFilters.html
//   beforeEach(function () {
//     module('BE.seed');
//   });

//   // inject AngularJS dependencies for the controller
//   beforeEach(inject(function ($controller, $rootScope, $uibModal, $q, export_service, $timeout) {
//     ctrl = $controller;
//     scope = $rootScope;
//     ctrl_scope = $rootScope.$new();
//     modal_state = '';
//     timeout = $timeout;

//     // mock the export_service factory methods used in the controller
//     // and return their promises
//     mock_export_service = export_service;
//     spyOn(mock_export_service, 'export_buildings')
//       .andCallFake(function () {
//         // return $q.reject for error scenario
//         return $q.when({status: 'success', export_id: '123456'});
//       });
//     spyOn(mock_export_service, 'export_buildings_progress')
//       .andCallFake(function () {
//         // return $q.reject for error scenario
//         return $q.when({
//           status: 'success',
//           buildings_processed: 1000
//         });
//       });
//     spyOn(mock_export_service, 'export_buildings_download')
//       .andCallFake(function () {
//         // return $q.reject for error scenario
//         return $q.when({
//           status: 'success',
//           url: '#'
//         });
//       });
//   }));

//   // this is outside the beforeEach so it can be configured by each unit test
//   function create_export_modal_controller () {
//     ctrl = ctrl('export_modal_controller', {
//       $scope: ctrl_scope,
//       $uibModalInstance: {
//         close: function () {
//           modal_state = 'close';
//         },
//         dismiss: function () {
//           modal_state = 'dismiss';
//         }
//       },
//       search: {
//         selected_buildings: [],
//         filter_params: {},
//         select_all_checkbox: false,
//         order_by: '',
//         sort_reverse: false,
//         number_matching_search: 1000
//       },
//       selected_fields: ['tax_lot_id', 'postal_code'],
//       project: {
//         id: 11
//       }
//     });
//   }

//   /**
//    * Test scenarios
//    */

//   it('should start at the create page', function () {
//     // arrange
//     create_export_modal_controller();

//     // act
//     ctrl_scope.$digest();

//     // assertions
//     expect(ctrl_scope.export_state).toEqual('create');
//   });
//   it('should start with an empty name and default file type of \'xls\'',
//     function () {
//       // arrange
//       create_export_modal_controller();

//       // act
//       ctrl_scope.$digest();

//       // assertions
//       var b = ctrl_scope.building_export;
//       expect(b.export_name).toEqual('');
//       expect(b.export_type).toEqual('xls');
//     });
//   it('should save the search parameters',
//     function () {
//       // arrange
//       create_export_modal_controller();

//       // act
//       ctrl_scope.$digest();

//       // assertions
//       var b = ctrl_scope.building_export;
//       expect(b.selected_buildings).toEqual([]);
//       expect(b.filter_params).toEqual({});
//       expect(b.order_by).toEqual('');
//       expect(b.sort_reverse).toEqual(false);
//       expect(b.select_all_checkbox).toEqual(false);
//       expect(b.selected_fields).toEqual(['tax_lot_id', 'postal_code']);
//       expect(b.project_id).toEqual(11);
//       expect(ctrl_scope.progress_denominator).toEqual(0);
//     });
//   it('should kick off the export process when the export button is clicked',
//     function () {
//       // arrange
//       create_export_modal_controller();

//       // act
//       ctrl_scope.$digest();
//       ctrl_scope.export_buildings();

//       // assertions
//       expect(ctrl_scope.export_state).toEqual('prepare');
//       expect(mock_export_service.export_buildings).toHaveBeenCalled();
//     });
//   it('should close the modal when the close function is called', function () {
//     // arrange
//     create_export_modal_controller();

//     // act
//     ctrl_scope.close();
//     ctrl_scope.$digest();

//     // assertions
//     expect(modal_state).toBe('close');
//   });

//   it('should cancel the modal when the cancel function is called', function () {
//     // arrange
//     create_export_modal_controller();

//     // act
//     ctrl_scope.cancel();
//     ctrl_scope.$digest();

//     // assertions
//     expect(modal_state).toBe('dismiss');
//   });


// });
