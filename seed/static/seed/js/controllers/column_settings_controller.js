/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.column_settings', [])
  .controller('column_settings_controller', [
    '$scope',
    '$q',
    '$state',
    '$stateParams',
    'Notification',
    'columns',
    'organization_payload',
    'auth_payload',
    'columns_service',
    'modified_service',
    'organization_service',
    'spinner_utility',
    'urls',
    'naturalSort',
    'flippers',
    '$translate',
    function ($scope,
              $q,
              $state,
              $stateParams,
              Notification,
              columns,
              organization_payload,
              auth_payload,
              columns_service,
              modified_service,
              organization_service,
              spinner_utility,
              urls,
              naturalSort,
              flippers,
              $translate) {
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;

      $scope.state = $state.current;

      var originalColumns = angular.copy(columns);
      $scope.columns = columns;
      var diff = {};

      $scope.filter_params = {};

      $scope.data_types = [
        {id: 'None', label: ''},
        {id: 'number', label: $translate.instant('Number')},
        {id: 'float', label: $translate.instant('Float')},
        {id: 'integer', label: $translate.instant('Integer')},
        {id: 'string', label: $translate.instant('Text')},
        {id: 'datetime', label: $translate.instant('Datetime')},
        {id: 'date', label: $translate.instant('Date')},
        {id: 'boolean', label: $translate.instant('Boolean')},
        {id: 'area', label: $translate.instant('Area')},
        {id: 'eui', label: $translate.instant('EUI')}
      ];

      $scope.change_merge_protection = function (column) {
        column.merge_protection = (column.merge_protection === 'Favor New') ? 'Favor Existing' : 'Favor New';
        $scope.setModified();
      };

      $scope.setModified = function () {
        $scope.columns_updated = false;
        updateDiff();
        if (_.isEmpty(diff)) {
          modified_service.resetModified();
        } else {
          modified_service.setModified();
        }
      };

      $scope.isModified = function () {
        return modified_service.isModified();
      };

      var updateDiff = function () {
        diff = {};

        var cleanColumns = angular.copy(columns);
        _.forEach(originalColumns, function (originalCol, index) {
          if (!_.isEqual(originalCol, cleanColumns[index])) {
            var modifiedKeys = _.reduce(originalCol, function (result, value, key) {
              return _.isEqual(value, cleanColumns[index][key]) ? result : result.concat(key);
            }, []);
            diff[originalCol.id] = _.pick(cleanColumns[index], modifiedKeys);
            if (_.includes(modifiedKeys, 'displayName')) {
              // Rename to match backend
              diff[originalCol.id].display_name = diff[originalCol.id].displayName;
              delete diff[originalCol.id].displayName;
            }
          }
        });
      };

      // Saves the modified columns
      $scope.save_settings = function () {
        $scope.columns_updated = false;

        var missingDisplayNames = _.filter(columns, {displayName: undefined});
        if (missingDisplayNames.length) {
          Notification.error('Error: ' + missingDisplayNames.length + ' required display name' + (missingDisplayNames.length > 1 ? 's are' : ' is') + ' empty');
          return;
        }

        var promises = [];
        _.forOwn(diff, function (delta, column_id) {
          promises.push(columns_service.patch_column_for_org($scope.org.id, column_id, delta));
        });

        spinner_utility.show();
        $q.all(promises).then(function (/*results*/) {
          $scope.columns_updated = true;
          modified_service.resetModified();
          var totalChanged = _.keys(diff).length;
          Notification.success('Successfully updated ' + totalChanged + ' column' + (totalChanged === 1 ? '' : 's'));
          $state.reload();
        }, function (data) {
          $scope.$emit('app_error', data);
        }).finally(function () {
          spinner_utility.hide();
        });
      };

    }]);
