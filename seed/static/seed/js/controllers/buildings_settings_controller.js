/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.buildings_settings', [])
.controller('buildings_settings_controller', [
  '$scope',
  '$modalInstance',
  'all_columns',
  'default_columns',
  'shared_fields_payload',
  'user_service',
  '$filter',
  '$routeParams',
  'project_payload',
  function(
    $scope,
    $modalInstance,
    all_columns,
    default_columns,
    shared_fields_payload,
    user_service,
    $filter,
    $routeParams,
    project_payload
  ) {
    $scope.user = {};
    $scope.user.project_slug = $routeParams.project_id;
    $scope.filter_params = {};
    $scope.controls = {
      select_all: false
    };
    $scope.project = project_payload.project;

    $scope.fields = all_columns.fields;
    $scope.fields = $scope.fields.map(function(c){
      c.checked = (default_columns.columns.indexOf(c.sort_column) > -1);
      return c;
    });
    // three columns of fields, NB. fields_1/3 are not copies but pointers
    $scope.fields_1 = $scope.fields.slice(0, $scope.fields.length/3);
    $scope.fields_2 = $scope.fields.slice($scope.fields.length/3, $scope.fields.length*2/3);
    $scope.fields_3 = $scope.fields.slice($scope.fields.length*2/3, $scope.fields.length);
    $scope.user.show_shared_buildings = shared_fields_payload.show_shared_buildings;

    $scope.$watch('filter_params.title', function(){
        if (!$scope.filter_params.title) {
            $scope.controls.select_all = false;
        }
    });

    /**
     * updates all the fields checkboxs to match the ``select_all`` checkbox
     */
    $scope.select_all_clicked = function () {
        var fields = $filter('filter')($scope.fields, $scope.filter_params);
        fields = fields.map(function (f) {
            return f.sort_column;
        });
        $scope.fields = $scope.fields.map(function (f) {
            if (~fields.indexOf(f.sort_column)) {
                f.checked = $scope.controls.select_all;
            }
            return f;
        });
    };

    /**
     * save_custom_view: saves the columns a user wants displayed for a table,
     *   and closes the modal
     */
    $scope.save_settings = function() {
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
        user_service.set_default_columns(columns, $scope.user.show_shared_buildings)
        .then(function (data) {
            //resolve promise
            $scope.settings_updated = true;
            $modalInstance.close(columns);
            location.reload();
        });
    };

}]);
