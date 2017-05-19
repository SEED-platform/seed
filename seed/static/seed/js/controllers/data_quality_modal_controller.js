/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.data_quality_modal', [])
.controller('data_quality_modal_controller', [
  '$scope',
  '$uibModalInstance',
  'search_service',
  'dataQualityResults',
  'name',
  'uploaded',
  'importFileId',
  function(
    $scope,
    $uibModalInstance,
    search_service,
    dataQualityResults,
    name,
    uploaded,
    importFileId
  ) {
    $scope.name = name;
    $scope.uploaded = moment.utc(uploaded).local().format('MMMM Do YYYY, h:mm:ss A Z');
    $scope.dataQualityResults = dataQualityResults || [];
    $scope.importFileId = importFileId;

    $scope.close = function () {
      $uibModalInstance.close();
    };

    var fields = [{
      sort_column: 'table_name',
      sortable: false,
      title: 'Table'
    }, {
      sort_column: 'address_line_1',
      sortable: true,
      title: 'Address Line 1'
    }, {
      sort_column: 'jurisdiction_tax_lot_id',
      sortable: true,
      title: 'Jurisdiction Tax Lot ID'
    }, {
      sort_column: 'pm_property_id',
      sortable: true,
      title: 'PM Property ID'
    }, {
      sort_column: 'tax_lot_id',
      sortable: true,
      title: 'Tax Lot ID'
    }, {
      sort_column: 'custom_id_1',
      sortable: true,
      title: 'Custom ID'
    }, {
      sort_column: 'formatted_field',
      sortable: false,
      title: 'Field'
    }, {
      sort_column: 'detailed_message',
      sortable: false,
      title: 'Error Message'
    }];
    var columns = _.map(fields, 'sort_column');
    _.forEach(fields, function(field) {
      field.checked = false;
      field.class = 'is_aligned_right';
      field.field_type = null;
      field.link = false;
      field.static = false;
      field.type = 'string';
    });

    $scope.sortData = function() {
      $scope.dataQualityResults = _.orderBy($scope.dataQualityResults, [$scope.search.sort_column], [$scope.search.sort_reverse ? 'desc' : 'asc']);
    };

    $scope.search = angular.copy(search_service);

    // Override storage, search, and filter functions
    $scope.search.init_storage = function (prefix) {
      // Check session storage for order and sort values.
      if (!_.isUndefined(Storage)) {
        $scope.search.prefix = prefix;

        // order_by & sort_column
        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy') !== null) {
          $scope.search.order_by = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
          $scope.search.sort_column = sessionStorage.getItem(prefix + ':' + 'seedBuildingOrderBy');
        }

        // sort_reverse
        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse') !== null) {
          $scope.search.sort_reverse = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingSortReverse'));
        }

        // filter_params
        if (sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams') !== null) {
          $scope.search.filter_params = JSON.parse(sessionStorage.getItem(prefix + ':' + 'seedBuildingFilterParams'));
        }
      }
    };
    $scope.search.column_prototype.toggle_sort = function () {
      if (this.sortable) {
        if ($scope.search.sort_column === this.sort_column) {
          $scope.search.sort_reverse = !$scope.search.sort_reverse;
        } else {
          $scope.search.sort_reverse = true;
          $scope.search.sort_column = this.sort_column;
        }

        if (!_.isUndefined(Storage)) {
          sessionStorage.setItem($scope.search.prefix + ':' + 'seedBuildingOrderBy', $scope.search.sort_column);
          sessionStorage.setItem($scope.search.prefix + ':' + 'seedBuildingSortReverse', $scope.search.sort_reverse);
        }

        $scope.search.order_by = this.sort_column;
        $scope.sortData();
      }
    };
    $scope.search.column_prototype.sorted_class = function () {
      if ($scope.search.sort_column === this.sort_column) {
        if ($scope.search.sort_reverse) {
          return 'sorted sort_asc';
        } else {
          return 'sorted sort_desc';
        }
      } else {
        return '';
      }
    };
    $scope.search.filter_search = function () {
      $scope.search.sanitize_params();
      _.forEach($scope.dataQualityResults, function (result) {
        if (!result.visible) result.visible = true;
        _.forEach(result.data_quality_results, function(row) {
          if (!row.visible) row.visible = true;
        });
      });
      _.forEach(this.filter_params, function(value, column) {
        value = value.toLowerCase();
        _.forEach($scope.dataQualityResults, function (result) {
          if (result.visible) {
            if (_.includes(['detailed_message', 'formatted_field', 'table_name'], column)) {
              _.forEach(result.data_quality_results, function(row) {
                if (!_.includes(row[column].toLowerCase(), value)) row.visible = false;
              });
            } else {
              if (_.isNull(result[column]) || !_.includes(result[column].toLowerCase(), value)) result.visible = false;
            }
          }
        });
      });
      if (!_.isUndefined(Storage)) {
        sessionStorage.setItem(this.prefix + ':' + 'seedBuildingFilterParams', JSON.stringify(this.filter_params));
      }
    };
    $scope.search.num_pages = 1;
    $scope.search.number_per_page = $scope.dataQualityResults.length;
    $scope.search.sort_column = null;
    $scope.search.init_storage('data_quality');
    if ($scope.search.sort_column !== null) $scope.sortData();
    $scope.search.filter_search();

    $scope.columns = $scope.search.generate_columns(
      fields,
      columns,
      $scope.search.column_prototype
    );
}]);
