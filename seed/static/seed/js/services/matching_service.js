/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

// matching services
angular.module('BE.seed.service.matching', []).factory('matching_service', [
  '$http',
  'user_service',
  'generated_urls',
  'spinner_utility',
  function ($http, user_service, generated_urls, spinner_utility) {

    var matching_service = {};

    /**
     *Start system matching
     *
     *@param import_file_id: int, the database id of the import file
     * we wish to match against other buildings for an organization.
     */
    matching_service.start_system_matching = function (import_file_id) {
      return $http.post('/api/v2/import_files/' + import_file_id + '/start_system_matching/', {
        organization_id: user_service.get_organization().id
      }).then(function (response) {
        return response.data;
      });
    };

    matching_service.available_matches = function (import_file_id, inventory_type, state_id) {
      return $http.post('/api/v2/import_files/' + import_file_id + '/available_matches/', {
        inventory_type: inventory_type,
        state_id: state_id
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    matching_service.unmatch = function (import_file_id, inventory_type, state_id, coparent_id) {
      spinner_utility.show();
      return $http.post('/api/v2/import_files/' + import_file_id + '/unmatch/', {
        inventory_type: inventory_type,
        state_id: state_id,
        coparent_id: coparent_id
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    matching_service.match = function (import_file_id, inventory_type, state_id, matching_state_id) {
      spinner_utility.show();
      return $http.post('/api/v2/import_files/' + import_file_id + '/match/', {
        inventory_type: inventory_type,
        state_id: state_id,
        matching_state_id: matching_state_id
      }, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    matching_service.saveVisibility = function (matchingVisibility) {
      var key = 'matchingVisibility.' + user_service.get_organization().id;
      localStorage.setItem(key, matchingVisibility);
    };

    matching_service.loadVisibility = function () {
      var key = 'matchingVisibility.' + user_service.get_organization().id;
      return localStorage.getItem(key) || 'Show All';
    };

    matching_service.reorderSettings = function (columns) {
      var selected = _.remove(columns, 'visible');
      return selected.concat(columns);
    };

    matching_service.removeLeftSettings = function (key) {
      key += '.left.' + user_service.get_organization().id;
      localStorage.removeItem(key);
    };

    matching_service.removeRightSettings = function (key) {
      key += '.right.' + user_service.get_organization().id;
      localStorage.removeItem(key);
    };

    matching_service.loadShowOnlyMappedFields = function () {
      var key = 'matching.showOnlyMappedFields.' + user_service.get_organization().id;
      return localStorage.getItem(key) !== 'false';
    };

    matching_service.saveShowOnlyMappedFields = function (showOnlyMappedFields) {
      var key = 'matching.showOnlyMappedFields.' + user_service.get_organization().id;
      return localStorage.setItem(key, showOnlyMappedFields);
    };

    matching_service.saveLeftColumns = function (key, columns) {
      key += '.left.' + user_service.get_organization().id;
      var toSave = matching_service.reorderSettings(_.map(columns, function (col) {
        return _.pick(col, ['name', 'visible']);
      }));
      localStorage.setItem(key, JSON.stringify(toSave));
    };

    matching_service.loadLeftColumns = function (key, columns) {
      var showOnlyMappedFields = matching_service.loadShowOnlyMappedFields();
      if (showOnlyMappedFields) return 'showOnlyMappedFields';

      key += '.left.' + user_service.get_organization().id;
      columns = angular.copy(columns);

      // Hide extra data columns by default
      _.forEach(columns, function (col) {
        col.visible = !col.extraData;
      });

      var localColumns = localStorage.getItem(key);
      if (!_.isNull(localColumns)) {
        var existingColumnNames = _.map(columns, 'name');
        localColumns = JSON.parse(localColumns);

        // Remove nonexistent columns
        _.remove(localColumns, function (col) {
          return !_.includes(existingColumnNames, col.name);
        });
        // Use saved column settings with original data as defaults
        localColumns = _.map(localColumns, function (col) {
          return _.defaults(col, _.remove(columns, {name: col.name})[0]);
        });
        // If no columns are visible, reset visibility only
        if (!_.find(localColumns, 'visible')) {
          _.forEach(localColumns, function (col) {
            col.visible = !col.extraData;
          });
        }
        return matching_service.reorderSettings(localColumns.concat(columns));
      } else {
        return matching_service.reorderSettings(columns);
      }
    };

    matching_service.saveRightColumns = function (key, columns) {
      key += '.right.' + user_service.get_organization().id;
      var toSave = matching_service.reorderSettings(_.map(columns, function (col) {
        return _.pick(col, ['name', 'visible']);
      }));
      localStorage.setItem(key, JSON.stringify(toSave));
    };

    matching_service.loadRightColumns = function (key, columns) {
      key += '.right.' + user_service.get_organization().id;
      columns = angular.copy(columns);

      // Hide extra data columns by default
      _.forEach(columns, function (col) {
        col.visible = !col.extraData;
      });

      var localColumns = localStorage.getItem(key);
      if (!_.isNull(localColumns)) {
        var existingColumnNames = _.map(columns, 'name');
        localColumns = JSON.parse(localColumns);

        // Remove nonexistent columns
        _.remove(localColumns, function (col) {
          return !_.includes(existingColumnNames, col.name);
        });
        // Use saved column settings with original data as defaults
        localColumns = _.map(localColumns, function (col) {
          return _.defaults(col, _.remove(columns, {name: col.name})[0]);
        });
        // If no columns are visible, reset visibility only
        if (!_.find(localColumns, 'visible')) {
          _.forEach(localColumns, function (col) {
            col.visible = !col.extraData;
          });
        }
        return matching_service.reorderSettings(localColumns.concat(columns));
      } else {
        return matching_service.reorderSettings(columns);
      }
    };

    matching_service.saveSort = function (key, settings) {
      key += '.' + user_service.get_organization().id;
      localStorage.setItem(key, JSON.stringify(settings));
    };

    matching_service.loadSort = function (key) {
      key += '.' + user_service.get_organization().id;
      return localStorage.getItem(key);
    };

    matching_service.removeSettings = function (key) {
      key += '.' + user_service.get_organization().id;
      localStorage.removeItem(key);
    };

    return matching_service;
  }]);
