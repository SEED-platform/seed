/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/*
 * concat_modal_ctrl, controls selecting columns to concatenate together.
 *
 */

angular.module('BE.seed.controller.concat_modal', [])
.controller('concat_modal_ctrl', [
  '$scope',
  '$uibModalInstance',
  'building_column_types',
  'raw_columns',
  function(
    $scope,
    $uibModalInstance,
    building_column_types,
    raw_columns
  ){
    $scope.raw_columns = raw_columns;
    $scope.building_columns = building_column_types;
    $scope.concat_columns = [];
    $scope.delimiter = ' ';
    $scope.target_tcm = {};

    /*
     * Create a concatenated TCM.
     *
     * Makes new name, and new raw data
     *
     */
    $scope.concatenate_columns = function() {
        var target_tcm = {};
        var target_names = [];
        var target_raw_data = [];
        // This is where we'll store intermediate data before we concat
        var concat_data = [
            [], [], [], [], []
        ];
        for (var i = 0; i < $scope.concat_columns.length; i++) {
            $scope.concat_columns[i].is_concat_parameter = true;
            target_names.push($scope.concat_columns[i].name);
            for (var j = 0; j < $scope.concat_columns[i].raw_data.length; j++){
                concat_data[j].push($scope.concat_columns[i].raw_data[j]);
            }
        }

        for (i = 0; i < concat_data.length; i++) {
            target_raw_data.push(
                concat_data[i].join($scope.delimiter)
            );
        }

        target_tcm.is_concatenated = true;
        // This is what we send back to the save_column_mappings function.
        target_tcm.source_headers = target_names;
        target_tcm.name = target_names.join($scope.delimiter);
        target_tcm.building_columns = $scope.building_columns;
        target_tcm.suggestion = $scope.concat_columns[0].suggestion;
        target_tcm.confidence = 1;
        target_tcm.user_suggestion = true;
        target_tcm.raw_data = target_raw_data;

        $scope.target_tcm = target_tcm;

    };

    /*
     * Creates a new TCM in $scope amoung the ``raw_columns``
     * Disables the concatenees from viewing.
     */
    $scope.save_concat = function() {
        $scope.concatenate_columns();
        if (typeof($scope.target_tcm) !== undefined) {
            $scope.raw_columns.push($scope.target_tcm);
        }
        $uibModalInstance.close();
    };

    $scope.close_concat_modal = function () {
        for (var i = 0; i < $scope.concat_columns.length; i++) {
            if ($scope.concat_columns[i].is_a_concat_parameter === false) {
                // Put back any concat_column elements that weren't turned into
                // a concatenated column.
                $scope.raw_columns.push($scope.concat_columns[i]);
            }
        }

        $uibModalInstance.close();
    };

  }
]);

