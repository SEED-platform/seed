/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.custom_view_modal', [])
.controller('custom_view_modal_ctrl', [
  '$scope',
  '$uibModalInstance',
  'all_columns',
  'selected_columns',
  'buildings_payload',
  'user_service',
  function($scope, $uibModalInstance, all_columns, selected_columns, buildings_payload, user_service) {
    $scope.my_buildings_count = buildings_payload.my_buildings_count;
    $scope.all_buildings_count = buildings_payload.all_buildings_count;
    $scope.fields = all_columns.fields;
    $scope.fields = $scope.fields.map(function(c){
      c.checked = (selected_columns.indexOf(c.sort_column) > -1);
      return c;
    });
    // three columns of fields, NB. fields_1/3 are not copies but pointers
    $scope.fields_1 = $scope.fields.slice(0, $scope.fields.length/3);
    $scope.fields_2 = $scope.fields.slice($scope.fields.length/3, $scope.fields.length*2/3);
    $scope.fields_3 = $scope.fields.slice($scope.fields.length*2/3, $scope.fields.length);
    $scope.user = {};


    /**
     * save_custom_view: saves the columns a user wants displayed for a table,
     *   and closes the modal
     */
    $scope.save_custom_view = function() {
        var columns = $scope.fields;
        // filter out unchecked columns
        columns = columns.filter(function(field){
            return field.checked;
        });
        // map the array of objects to an array of column names
        columns = columns.map(function(field) {
            return field.sort_column;
        });
        // save the array of column names for the user
        user_service.set_default_columns(columns, $scope.user.show_shared_buildings);
        $uibModalInstance.close(columns);
    };

    /**
     * fetches the user's ``show_shared_buildings``
     */
    var init = function() {
      user_service.get_shared_buildings().then(function(data){
        $scope.user.show_shared_buildings = data.show_shared_buildings;
      });
    };
    init();
}]);
