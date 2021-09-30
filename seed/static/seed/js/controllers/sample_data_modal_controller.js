/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.sample_data_modal', [])
  .controller('sample_data_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'inventory_service',
    'organization_service',
    'organization',
    'cycle',
    'profiles',
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      inventory_service,
      organization_service,
      organization,
      cycle,
      profiles
    ) {
      $scope.inProgress = false;
      $scope.hasData = cycle.num_properties > 0 || cycle.num_taxlots > 0;

      $scope.continue = function () {
        $scope.inProgress = true;

        // Create column list profile if it doesn't exist
        let foundProfile = profiles.find(({name, profile_location}) => name === 'Auto-Populate' && profile_location === 'List View Profile');
        let profilePromise;
        if (foundProfile) {
          profilePromise = new Promise(resolve => resolve(foundProfile));
        } else {
          profilePromise = inventory_service.new_column_list_profile({
            name: 'Auto-Populate',
            profile_location: 'List View Profile',
            inventory_type: 'Property',
            columns: [],
            derived_columns: []
          });
        }

        // 1. Insert sample data
        // 2. Get all columns
        // 3. Get all properties
        // 4. Find only populated columns, and save to column list profile Auto-Populate
        profilePromise.then(profile => {
          inventory_service.save_last_profile(profile.id, 'properties');
          inventory_service.save_last_cycle(cycle.id)

          return organization_service.insert_sample_data(organization.org_id).then(() => {
            return inventory_service.get_property_columns().then(columns => {
              return inventory_service.get_properties(1, undefined, cycle, -1).then(inventory => {
                const visibleColumns = findPopulatedColumns(columns, inventory.results);
                const profileId = profile.id;
                profile = _.omit(profile, 'id');
                profile.columns = visibleColumns;
                return inventory_service.update_column_list_profile(profileId, profile);
              });
            });
          }).catch(response => {
            let msg = 'Error: Failed to insert sample data';
            if (response.data.message) {
              msg = `${msg} (${response.data.message})`;
            }
            Notification.error(msg);
            return Promise.reject();
          });
        }).then(() => {
          $uibModalInstance.close();
          $state.go('inventory_list', {inventory_type: 'properties'});
        }).finally(() => {
          $scope.inProgress = false;
        });
      };

      $scope.cancel = function () {
        $uibModalInstance.dismiss();
      };

      function notEmpty(value) {
        return !_.isNil(value) && value !== '';
      }

      function findPopulatedColumns(allColumns, inventory) {
        const cols = _.reject(allColumns, 'related');
        const relatedCols = _.filter(allColumns, 'related');

        _.forEach(inventory, function (record) {
          _.forEachRight(cols, function (col, colIndex) {
            if (notEmpty(record[col.name])) {
              cols.splice(colIndex, 1);
            }
          });

          _.forEach(record.related, function (relatedRecord) {
            _.forEachRight(relatedCols, function (col, colIndex) {
              if (notEmpty(relatedRecord[col.name])) {
                relatedCols.splice(colIndex, 1);
              }
            });
          });
        });

        // determine hidden columns
        const visible = _.reject(allColumns, function (col) {
          if (!col.related) {
            return _.find(cols, {id: col.id});
          }
          return _.find(relatedCols, {id: col.id});
        });

        const hidden = _.reject(allColumns, function (col) {
          return _.find(visible, {id: col.id});
        });

        _.forEach(hidden, function (col) {
          col.visible = false;
        });

        const columns = [];
        _.forEach(visible, function (col) {
          columns.push({
            column_name: col.column_name,
            id: col.id,
            order: columns.length + 1,
            pinned: false,
            table_name: col.table_name
          });
        });

        return columns;
      }
    }]);
