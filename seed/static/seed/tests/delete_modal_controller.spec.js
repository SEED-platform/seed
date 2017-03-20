/**
 * :copyright: (c) 2014 Building Energy Inc
 */

// This controller is no longer used.

// describe('controller: delete_modal_controller', function(){
//     // globals set up and used in each test scenario
//     var mock_building_services, scope, controller, modal_state;
//     var ctrl, ctrl_scope, modalInstance, timeout;
//     beforeEach(function() {
//         module('BE.seed');
//     });

//     // inject AngularJS dependencies for the controller
//     beforeEach(inject(function($controller, $rootScope, $uibModal, $q, building_services, $timeout) {
//         ctrl = $controller;
//         scope = $rootScope;
//         ctrl_scope = $rootScope.$new();
//         modal_state = '';
//         timeout = $timeout;

//         // mock the export_service factory methods used in the controller
//         // and return their promises
//         mock_building_services = building_services;
//         spyOn(mock_building_services, 'delete_buildings')
//             .andCallFake(function(){
//                 // return $q.reject for error scenario
//                 return $q.when({status: 'success'});
//             }
//         );
//         spyOn(mock_building_services, 'get_total_number_of_buildings_for_user')
//             .andCallFake(function(){
//                 return $q.when({status:'success'});
//             });
//     }));

//     // this is outside the beforeEach so it can be configured by each unit test
//     function create_delete_modal_controller(){
//         ctrl = ctrl('delete_modal_controller', {
//             $scope: ctrl_scope,
//             $uibModalInstance: {
//                 close: function() {
//                     modal_state = 'close';
//                 },
//                 dismiss: function() {
//                     modal_state = 'dismiss';
//                 }
//             },
//             search: {
//                 selected_buildings: [1, 2],
//                 filter_params: {},
//                 select_all_checkbox: false,
//                 order_by: '',
//                 sort_reverse: false,
//                 number_matching_search: 1000
//             }
//         });
//     }

//     /*
//      * Test scenarios
//      */

//     it('should start at the delete page', function() {
//         // arrange
//         create_delete_modal_controller();

//         // act
//         ctrl_scope.$digest();

//         // assertions
//         expect(ctrl_scope.delete_state).toEqual('delete');
//     });
//     it('should save the search paramaters',
//         function() {
//         // arrange
//         create_delete_modal_controller();

//         // act
//         ctrl_scope.$digest();

//         // assertions
//         var b = ctrl_scope.delete_payload;
//         expect(b.selected_buildings).toEqual([1, 2]);
//         expect(b.filter_params).toEqual({});
//         expect(b.order_by).toEqual('');
//         expect(b.sort_reverse).toEqual(false);
//         expect(b.select_all_checkbox).toEqual(false);
//     });
//     it('should delete when the delete button is clicked',
//         function() {
//         // arrange
//         create_delete_modal_controller();

//         // act
//         ctrl_scope.$digest();
//         ctrl_scope.delete_buildings();

//         // assertions
//         expect(ctrl_scope.delete_state).toEqual('prepare');
//         expect(mock_building_services.delete_buildings).toHaveBeenCalled();
//     });
//     it('should show the success page when the delete is finished',
//         function() {
//         // arrange
//         create_delete_modal_controller();

//         // act
//         ctrl_scope.$digest();
//         ctrl_scope.delete_buildings();
//         ctrl_scope.$digest();

//         // assertions
//         expect(mock_building_services.delete_buildings).toHaveBeenCalled();
//         // expect(mock_building_services.get_total_number_of_buildings_for_user).toHaveBeenCalled();
//         expect(ctrl_scope.delete_state).toEqual('success');
//     });
//     it('should show the number of buildings to be deleted',
//         function() {
//         // arrange
//         create_delete_modal_controller();

//         // act
//         ctrl_scope.$digest();
//         var number_to_delete = ctrl_scope.number_to_delete();

//         // assertions
//         expect(number_to_delete).toEqual(2);
//     });
//     it('should close the modal when the close function is called', function() {
//         // arrange
//         create_delete_modal_controller();

//         // act
//         ctrl_scope.close();
//         ctrl_scope.$digest();

//         // assertions
//         expect(modal_state).toBe('close');
//     });

//     it('should cancel the modal when the cancel funtion is called', function() {
//         // arrange
//         create_delete_modal_controller();

//         // act
//         ctrl_scope.cancel();
//         ctrl_scope.$digest();

//         // assertions
//         expect(modal_state).toBe('dismiss');
//     });
// });
