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
    // re-check the user's selected columns
    $scope.fields = $scope.fields.map(function(c){
      c.checked = (default_columns.columns.indexOf(c.sort_column) > -1);
      return c;
    });
    // also put the selected columns in the saved order, in case they were reordered
    $scope.fields.sort(function(a,b) {
        if (a.checked && b.checked) {
            return default_columns.columns.indexOf(a.sort_column) - default_columns.columns.indexOf(b.sort_column);
        } else if (!a.checked && !b.checked) {
            // rest alphabetical
            return (a.title < b.title ? -1 : (a.title > b.title ? 1 : 0));
        } else {
            // just one is checked
            return (a.checked ? -1 : 1);
        }
    });
    // three columns of fields, NB. fields_1/3 are not copies but pointers
    $scope.fields_1 = $scope.fields.slice(0, $scope.fields.length/3);
    $scope.fields_2 = $scope.fields.slice($scope.fields.length/3, $scope.fields.length*2/3);
    $scope.fields_3 = $scope.fields.slice($scope.fields.length*2/3, $scope.fields.length);
    $scope.user.show_shared_buildings = shared_fields_payload.show_shared_buildings;

    // configure the list sorting options.  Consider moving this somewhere global if reusing in more places.
    $scope.sortable_options = {
        cursor: 'move',
        axis: 'y'
    };

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

    /**
    * when the user is ready to reorder the fields,
     * put the checked ones at the top
     * but keep the checked ones in their previous order, don't reorder those
    */
    $scope.on_show_reorder_fields = function() {
        var columns = $scope.fields;
        // filter out unchecked columns
        columns = columns.filter(function(field){
            return field.checked;
        });
        // map the array of objects to an array of column names
        columns = columns.map(function(field) {
            return field.sort_column;
        });
        $scope.fields.sort(function(a,b) {
          if (a.checked && b.checked) {
              return (columns.indexOf(a.sort_column) - columns.indexOf(b.sort_column));
          } else if (!a.checked && !b.checked) {
              return (a.title < b.title ? -1 : (a.title > b.title ? 1 : 0));
          } else {
              return (a.checked ? -1 : 1);
          }
        });
        $scope.is_show_reorder = true;
    }


  }]);
