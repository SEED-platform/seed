/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.delete_modal', [])
.controller('delete_modal_controller', [
  '$scope',
  '$modalInstance',
  'search',
  'building_services',
  function($scope, $modalInstance, search, building_services) {
    $scope.delete_state = 'delete';
    $scope.delete_payload = {};
    $scope.delete_payload.selected_buildings = search.selected_buildings;
    $scope.delete_payload.filter_params = search.filter_params;
    $scope.delete_payload.select_all_checkbox = search.select_all_checkbox;
    $scope.delete_payload.order_by = search.order_by;
    $scope.delete_payload.sort_reverse = search.sort_reverse;

    /**
     * delete_buildings: calls the delete process
     */
    $scope.delete_buildings = function () {
        $scope.progress_percentage = 0;
        $scope.delete_state = 'prepare';
        building_services.delete_buildings($scope.delete_payload).then(
          function (data) {
            // resolve promise
            $scope.delete_state = 'success';
          }
        ).then(
          function(){
            //update building count. 
            building_services.get_total_number_of_buildings_for_user().then(
              function (data){
                //we don't need to do anything with the data as it's bound to relevant UI
              });
          }
        );
    };

    /**
     * returns the number of buildings that will be deleted
     * @return {int} number of buildings that will be deleted
     */
    $scope.number_to_delete = function () {
        if (search.select_all_checkbox) {
            return search.number_matching_search - search.selected_buildings.length;
        } else {
            return search.selected_buildings.length;
        }
    };

    /**
     * cancel: dismisses the modal
     */
    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };

    /**
     * close: closes the modal
     */
    $scope.close = function () {
        $modalInstance.close();
    };
}]);
