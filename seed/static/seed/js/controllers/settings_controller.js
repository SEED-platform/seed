/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.organization_settings', [])
.controller('settings_controller', [
    '$scope',
    '$log',
    'all_columns',
    'organization_payload',
    'query_threshold_payload',
    'shared_fields_payload',
    'auth_payload',
    'organization_service',
    '$filter',
    'user_service',
    function (
      $scope,
      $log,
      all_columns,
      organization_payload,
      query_threshold_payload,
      shared_fields_payload,
      auth_payload,
      organization_service,
      $filter,
      user_service
    ) {
    $scope.fields = all_columns.fields;
    $scope.org = organization_payload.organization;
    $scope.filter_params = {};
    $scope.org.query_threshold = query_threshold_payload.query_threshold;
    $scope.auth = auth_payload.auth;
    $scope.infinite_fields = $scope.fields.slice(0, 20);
    $scope.controls = {
        select_all: false
    };
    
    $scope.$watch('filter_params.title', function(){
        if (!$scope.filter_params.title) {
            $scope.controls.select_all = false;
        }
    });

    /**
     * infinite paging
     */
    $scope.add_more_fields = function() {
        var last_index = $scope.infinite_fields.length;
        var fields = $filter('filter')($scope.fields, $scope.filter_params);
        for (var i = 0; i < 20 && (last_index + i) < fields.length; i++){
            var field = angular.copy(fields[i + last_index]);
            field.checked = $scope.controls.select_all;
            $scope.infinite_fields.push(field);
        }
    };

    /**
     * updates all the fields checkboxes to match the ``select_all`` checkbox
     */
    $scope.select_all_clicked = function (type) {
        var fields = $filter('filter')($scope.fields, $scope.filter_params);
        fields = fields.map(function (f) {
            return f.sort_column;
        });
        if (type === 'internal') {
            $scope.fields = $scope.fields.map(function (f) {
                if (~fields.indexOf(f.sort_column)) {
                    f.checked = $scope.controls.select_all;
                }
                return f;
            });
        } else if (type === 'public') {
            $scope.fields = $scope.fields.map(function (f) {
                if (~fields.indexOf(f.sort_column)) {
                    f.public_checked = $scope.controls.public_select_all;
                }
                return f;
            });
        }
    };

    /**
     * saves the updates settings
     */
    $scope.save_settings = function () {
        var fields = $scope.fields.filter(function (f) {
            return f.checked;
        });
        $scope.org.fields = fields;
        $scope.org.public_fields = $scope.fields.filter(function (f) {
            return f.public_checked;
        });
        organization_service.save_org_settings($scope.org).then(function (data){
            // resolve promise
            $scope.settings_updated = true;
        }, function (data, status) {
            // reject promise
            $scope.$emit('app_error', data);
        });
    };

    /**
     * preforms from initial data processing:
     * - sets the checked shared fields
     */
    var init = function () {
        var sort_columns = shared_fields_payload.shared_fields.map(function (f) {
            return f.sort_column;
        });
        var public_columns = shared_fields_payload.public_fields.map(function (f) {
            return f.sort_column;
        });
        $scope.fields = $scope.fields.map(function (f) {
            if (sort_columns.indexOf(f.sort_column) !== -1) {
                f.checked = true;
            }
            if (public_columns.indexOf(f.sort_column) !== -1) {
                f.public_checked = true;
            }
            return f;
        });
    };
    init();

}]);
