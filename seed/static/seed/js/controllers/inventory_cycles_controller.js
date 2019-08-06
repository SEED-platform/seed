/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_cycles', [])
  .controller('inventory_cycles_controller', [
    '$scope',
    '$filter',
    '$window',
    '$uibModal',
    '$sce',
    '$stateParams',
    'inventory_service',
    'user_service',
    'inventory',
    'cycles',
    'profiles',
    'current_profile',
    'all_columns',
    'urls',
    'spinner_utility',
    'naturalSort',
    '$translate',
    'uiGridConstants',
    'i18nService', // from ui-grid
    function (
      $scope,
      $filter,
      $window,
      $uibModal,
      $sce,
      $stateParams,
      inventory_service,
      user_service,
      inventory,
      cycles,
      profiles,
      current_profile,
      all_columns,
      urls,
      spinner_utility,
      naturalSort,
      $translate,
      uiGridConstants,
      i18nService
    ) {
      spinner_utility.show();
      $scope.inventory_type = $stateParams.inventory_type;

      $scope.cycle = {
        selected_cycle: _.find(cycles.cycles, {id: inventory.cycle_id}),
        cycles: cycles.cycles
      };

      $scope.data = _.reduce(inventory, function(all_records, records, cycle_id) {
        var cycle = _.find($scope.cycle.cycles, { id: parseInt(cycle_id) });
        _.forEach(records, function(record) {
          record.cycle_name = cycle.name;
          all_records.push(record)
        })
        return all_records
      }, [])

      // set up i18n
      //
      // let angular-translate be in charge ... need
      // to feed the language-only part of its $translate setting into
      // ui-grid's i18nService
      var stripRegion = function (languageTag) {
        return _.first(languageTag.split('_'));
      };
      i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

      // List Settings Profile
      $scope.profiles = profiles;
      $scope.currentProfile = current_profile;

      if ($scope.currentProfile) {
        $scope.columns = [];
        _.forEach($scope.currentProfile.columns, function (col) {
          var foundCol = _.find(all_columns, {id: col.id});
          if (foundCol) {
            foundCol.pinnedLeft = col.pinned;
            $scope.columns.push(foundCol);
          }
        });
      } else {
        // No profiles exist
        $scope.columns = _.reject(all_columns, 'is_extra_data');
      }

      var defaults = {
        headerCellFilter: 'translate',
        minWidth: 75,
        width: 150
      };
      _.map($scope.columns, function (col) {
        var options = {};
        if (col.data_type === 'datetime') {
          options.cellFilter = 'date:\'yyyy-MM-dd h:mm a\'';
        }
        return _.defaults(col, options, defaults);
      });

      $scope.columns.unshift(
        {
          data_type: "integer",
          displayName: 'Linking ID',
          grouping: { groupPriority: 0 },
          name: 'id',
          sort: { priority: 0, direction: 'desc' },
          // visible: false,
          minWidth: 75,
          width: 150
        },
        {
          name: "cycle_name",
          data_type: "string",
          displayName: "Cycle",
          minWidth: 75,
          width: 150
        }
      )

      $scope.gridOptions = {
        data: 'data',
        columnDefs: $scope.columns,
      };

      // console.log("currentProfile", $scope.currentProfile);
      // console.log("all_columns", all_columns);
      // console.log("data", $scope.data);
      // console.log("cycle", $scope.cycle);
      // console.log('inventory', inventory);
      // console.log('columns', $scope.columns);
    }]);
