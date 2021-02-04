/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// inventory services
angular.module('BE.seed.service.inventory', []).factory('inventory_service', [
  '$http',
  '$log',
  '$q',
  'urls',
  'user_service',
  'cycle_service',
  'spinner_utility',
  'naturalSort',
  'Notification',
  function ($http, $log, $q, urls, user_service, cycle_service, spinner_utility, naturalSort, Notification) {

    var inventory_service = {
      total_properties_for_user: 0,
      total_taxlots_for_user: 0
    };

    inventory_service.get_properties = function (page, per_page, cycle, profile_id, property_view_ids, save_last_cycle=true) {

      var params = {
        organization_id: user_service.get_organization().id,
        page: page,
        per_page: per_page || 999999999
      };

      return cycle_service.get_cycles().then(function (cycles) {
        var validCycleIds = _.map(cycles.cycles, 'id');

        var lastCycleId = inventory_service.get_last_cycle();
        if (_.has(cycle, 'id')) {
          params.cycle = cycle.id;
          if (save_last_cycle === true) {
            inventory_service.save_last_cycle(cycle.id);
          }
        } else if (_.includes(validCycleIds, lastCycleId)) {
          params.cycle = lastCycleId;
        }

        return $http.post('/api/v3/properties/filter/', {
          // Pass the specific ids if they exist
          property_view_ids,
          // Pass the current profile (if one exists) to limit the column data that is returned
          profile_id: profile_id
        }, {
          params: params
        }).then(function (response) {
          return response.data;
        });
      }).catch(_.constant('Error fetching cycles'));
    };

    inventory_service.properties_cycle = function (profile_id, cycle_ids) {
      return $http.post('/api/v3/properties/filter_by_cycle/', {
        organization_id: user_service.get_organization().id,
        profile_id: profile_id,
        cycle_ids: cycle_ids
      }).then(function (response) {
        return response.data;
      });
    };

    /** Get Property information from server for a specified Property and Cycle and Organization.
     *
     *  @param property_id         The id of the requested Property
     *  @param cycle_id            The id of the requested Cycle for the requested Property
     *
     *  @returns {Promise}
     *
     *  The returned Property object (if the promise resolves successfully) will have a 'state' key with
     *  object containing all key/values for Property State (including 'extra_data')
     *  and a 'cycle' key with an object with at least the "id" key for that Cycle.
     *
     *  An example of structure of the returned JSON is...
     *
     *  {
     *    'property' {
     *      'id': 4,
     *      ..other Property fields...
     *     },
     *    'cycle': {
     *      'id': 1,
     *      ...other Cycle fields...
     *     },
     *     'taxlots': [
     *      ...array of objects with related TaxLot information...
     *     ],
     *     'state': {
     *        ...various key/values for Property state...
     *        extra_data : {
     *          ..various key/values for extra data...
     *        }
     *     }
     *     'changed_fields': {
     *        'regular_fields' : [
     *          ..list of keys for regular fields that have changed since last state
     *         ],
     *        'extra_data_fields' : [
     *          ..list of keys for extra_data fields that have changed since last state
     *         ]
     *      },
     *     'history' : [
     *        {
     *          'state': {
     *            ...various key/values for Property state...
     *              extra_data : {
     *                ..various key/values for extra data...
     *              }
     *           },
     *           'changed_fields': {
     *               'regular_fields' : [
     *                  ..list of keys for regular fields that have changed since last state
     *                ],
     *                'extra_data_fields' : [
     *                  ..list of keys for extra_data fields that have changed since last state
     *                ]
     *           },
     *           'date_edited': '2016-07-26T15:55:10.180Z'
     *           'source' : source of edit (ImportFile or UserEdit)
     *           'filename' : name of file if source=ImportFile
     *        },
     *        ... more history state objects...
     *     ]
     *     'status' : ('success' or 'error')
     *     'message' : (error message or empty string)
     *  }
     *
     */

    inventory_service.properties_meters_exist = function (property_view_ids) {
      return $http.post('/api/v3/properties/meters_exist/', {
        property_view_ids
      }, {
        params: { organization_id: user_service.get_organization().id }
      }).then(function (response) {
        return response.data;
      });
    };

    inventory_service.get_property = function (view_id) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_property(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.get('/api/v3/properties/' + view_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    inventory_service.get_property_links = function (view_id) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_property_links(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.get('/api/v3/properties/' + view_id + '/links/', {
        params: { organization_id: user_service.get_organization().id }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    inventory_service.property_match_merge_link = function (view_id) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.property_match_merge_link(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.post('/api/v3/properties/' + view_id + '/match_merge_link/', {}, {
        params: { organization_id: user_service.get_organization().id }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    /** Update Property State for a specified property view and organization.
     *
     * @param view_id             Property View ID of the property view
     * @param state               A Property state object, which should include key/values for
     *                              all state values
     *
     * @returns {Promise}
     */
    inventory_service.update_property = function (view_id, state) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.update_property(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(state)) {
        $log.error('#inventory_service.update_property(): state is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();

      return $http.put('/api/v3/properties/' + view_id + '/', {
        state: state
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


    inventory_service.delete_property_states = function (property_view_ids) {
      return $http.delete('/api/v3/properties/batch_delete/', {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: { property_view_ids },
        params: { organization_id: user_service.get_organization().id },
      });
    };


    inventory_service.delete_taxlot_states = function (taxlot_view_ids) {
      return $http.delete('/api/v3/taxlots/batch_delete/', {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: { taxlot_view_ids },
        params: { organization_id: user_service.get_organization().id }
      });
    };


    inventory_service.get_taxlots = function (page, per_page, cycle, profile_id, inventory_ids, save_last_cycle=true) {
      var params = {
        organization_id: user_service.get_organization().id,
        page: page,
        per_page: per_page || 999999999
      };

      return cycle_service.get_cycles().then(function (cycles) {
        var validCycleIds = _.map(cycles.cycles, 'id');

        var lastCycleId = inventory_service.get_last_cycle();
        if (cycle) {
          params.cycle = cycle.id;
          if (save_last_cycle === true) {
            inventory_service.save_last_cycle(cycle.id);
          }
        } else if (_.includes(validCycleIds, lastCycleId)) {
          params.cycle = lastCycleId;
        }

        return $http.post('/api/v3/taxlots/filter/', {
          // Pass the specific ids if they exist
          inventory_ids: inventory_ids,
          // Pass the current profile (if one exists) to limit the column data that is returned
          profile_id: profile_id
        }, {
          params: params
        }).then(function (response) {
          return response.data;
        });
      }).catch(_.constant('Error fetching cycles'));
    };

    inventory_service.taxlots_cycle = function (profile_id, cycle_ids) {
      return $http.post('/api/v3/taxlots/filter_by_cycle/', {
        organization_id: user_service.get_organization().id,
        profile_id: profile_id,
        cycle_ids: cycle_ids
      }).then(function (response) {
        return response.data;
      });
    };

    /** Get TaxLot information from server for a specified TaxLot and Cycle and Organization.
     *
     *
     * @param taxlot_id         The id of the TaxLot object to retrieve
     * @param cycle_id          The id of the particular cycle for the requested TaxLot
     *
     * @returns {Promise}
     *
     * The returned TaxLot object (if the promise resolves successfully) will have a 'state' key with
     * object containing all key/values for TaxLot State (including 'extra_data')
     * and a 'cycle' key with an object with at least the "id" key for that Cycle.
     *
     *
     *  An example of structure of the returned JSON is...
     *
     *  {
     *    'taxlot' {
     *      'id': 4,
     *      ..other Property fields...
     *     },
     *    'cycle': {
     *      'id': 1,
     *      ...other Cycle fields...
     *     },
     *     'properties': [
     *      ...array of objects with related Property information...
     *     ],
     *     'state': {
     *        ...various key/values for TaxLot state...
     *        extra_data : {
     *          ..various key/values for extra data...
     *        }
     *     }
     *     'changed_fields': {
     *        'regular_fields' : [
     *          ..list of keys for regular fields that have changed since last state
     *         ],
     *        'extra_data_fields' : [
     *          ..list of keys for extra_data fields that have changed since last state
     *         ]
     *      },
     *     'history' : [
     *        {
     *          'state': {
     *              ...various key/values for TaxLot state...
     *              extra_data : {
     *                ..various key/values for extra data...
     *              }
     *           },
     *           'changed_fields': {
     *               'regular_fields' : [
     *                  ..list of keys for regular fields that have changed since last state
     *                ],
     *                'extra_data_fields' : [
     *                  ..list of keys for extra_data fields that have changed since last state
     *                ]
     *           },
     *           'date_edited': '2016-07-26T15:55:10.180Z'
     *           'source' : source of edit (ImportFile or UserEdit)
     *           'filename' : name of file if source=ImportFile
     *        },
     *        ... more history state objects...
     *     ]
     *     'status' : ('success' or 'error')
     *     'message' : (error message or empty string)
     *  }
     *
     */


    inventory_service.get_taxlot = function (view_id) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_taxlot(): null view_id parameter');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.get('/api/v3/taxlots/' + view_id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    inventory_service.get_taxlot_links = function (view_id) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_taxlot_links(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.get('/api/v3/taxlots/' + view_id + '/links/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    inventory_service.taxlot_match_merge_link = function (view_id) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.taxlot_match_merge_link(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.post('/api/v3/taxlots/' + view_id + '/match_merge_link/', {}, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    /** Update Tax Lot State for a specified Tax Lot View and organization.
     *
     * @param view_id             Tax Lot View ID of the tax lot view
     * @param state               A Tax Lot state object, which should include key/values for
     *                              all state values
     *
     * @returns {Promise}
     */
    inventory_service.update_taxlot = function (view_id, state) {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.update_taxlot(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(state)) {
        $log.error('#inventory_service.update_taxlot(): state is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.put('/api/v3/taxlots/' + view_id + '/', {
        state: state
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

    inventory_service.get_last_cycle = function () {
      var organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('cycles')) || {})[organization_id];
    };

    inventory_service.save_last_cycle = function (pk) {
      var organization_id = user_service.get_organization().id,
        cycles = JSON.parse(localStorage.getItem('cycles')) || {};
      cycles[organization_id] = _.toInteger(pk);
      localStorage.setItem('cycles', JSON.stringify(cycles));
    };

    inventory_service.get_last_selected_cycles = function () {
      var organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('selected_cycles')) || {})[organization_id];
    };

    inventory_service.save_last_selected_cycles = function (ids) {
      var organization_id = user_service.get_organization().id;
      var selected_cycles = JSON.parse(localStorage.getItem('selected_cycles')) || {};
      selected_cycles[organization_id] = ids;
      localStorage.setItem('selected_cycles', JSON.stringify(selected_cycles));
    };

    inventory_service.get_last_profile = function (key) {
      var organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('profiles.' + key)) || {})[organization_id];
    };

    inventory_service.save_last_profile = function (pk, key) {
      var organization_id = user_service.get_organization().id,
        profiles = JSON.parse(localStorage.getItem('profiles.' + key)) || {};
      profiles[organization_id] = _.toInteger(pk);
      localStorage.setItem('profiles.' + key, JSON.stringify(profiles));
    };

    inventory_service.get_last_detail_profile = function (key) {
      var organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('detailProfiles.' + key)) || {})[organization_id];
    };

    inventory_service.save_last_detail_profile = function (pk, key) {
      var organization_id = user_service.get_organization().id,
        profiles = JSON.parse(localStorage.getItem('detailProfiles.' + key)) || {};
      profiles[organization_id] = _.toInteger(pk);
      localStorage.setItem('detailProfiles.' + key, JSON.stringify(profiles));
    };

    inventory_service.get_property_column_names_for_org = function (org_id) {
      return $http.get('/api/v3/columns/', {
        params: {
          inventory_type: 'property',
          organization_id: org_id,
          only_used: false,
          display_units: true
        }
      }).then(function (response) {
        let property_columns = response.data.columns.filter(column => column.table_name == 'PropertyState');
        return property_columns.map(a => {
          return { 'column_name': a.column_name, 'display_name': a.display_name };
        });
      });
    };

    inventory_service.get_taxlot_column_names_for_org = function (org_id) {
      return $http.get('/api/v3/columns/', {
        params: {
          inventory_type: 'taxlot',
          organization_id: org_id,
          only_used: false,
          display_units: true
        }
      }).then(function (response) {
        let taxlot_columns = response.data.columns.filter(column => column.table_name == 'TaxLotState');
        return taxlot_columns.map(a => {
          return { 'column_name': a.column_name, 'display_name': taxlot_columns.find(x => x.column_name == a.column_name).display_name };
        });
      });
    };

    inventory_service.get_property_columns = function () {
      return inventory_service.get_property_columns_for_org(user_service.get_organization().id);
    };

    inventory_service.get_property_columns_for_org = function (org_id, only_used, display_units = true) {
      if (only_used === undefined) only_used = false;
      return $http.get('/api/v3/columns/', {
        params: {
          inventory_type: 'property',
          organization_id: org_id,
          only_used: only_used,
          display_units: display_units
        }
      }).then(function (response) {
        // Remove empty columns
        var columns = _.filter(response.data.columns, function (col) {
          return !_.isEmpty(col.name);
        });

        // Rename display_name to displayName (ui-grid compatibility)
        columns = _.map(columns, function (col) {
          return _.mapKeys(col, function (value, key) {
            return key === 'display_name' ? 'displayName' : key;
          });
        });

        // Remove _orig columns
        // if (flippers.is_active('release:orig_columns')) {
        //   _.remove(columns, function (col) {
        //     return /_orig/.test(col.name);
        //   });
        // }

        // Check for problems
        var duplicates = _.filter(_.map(columns, 'name'), function (value, index, iteratee) {
          return _.includes(iteratee, value, index + 1);
        });
        if (duplicates.length) {
          $log.error('Duplicate property column names detected:', duplicates);
        }

        return columns;
      });
    };

    inventory_service.get_mappable_property_columns = function () {
      return $http.get('/api/v3/columns/mappable/', {
        params: {
          organization_id: user_service.get_organization().id,
          inventory_type: 'property',
        }
      }).then(function (response) {
        // Remove empty columns
        var columns = _.filter(response.data.columns, function (col) {
          return !_.isEmpty(col.name);
        });

        // Rename display_name to displayName (ui-grid compatibility)
        columns = _.map(columns, function (col) {
          return _.mapKeys(col, function (value, key) {
            return key === 'display_name' ? 'displayName' : key;
          });
        });

        // Remove _orig columns
        // if (flippers.is_active('release:orig_columns')) {
        //   _.remove(columns, function (col) {
        //     return /_orig/.test(col.name);
        //   });
        // }

        // Check for problems
        var duplicates = _.filter(_.map(columns, 'name'), function (value, index, iteratee) {
          return _.includes(iteratee, value, index + 1);
        });
        if (duplicates.length) {
          $log.error('Duplicate property column names detected:', duplicates);
        }

        return columns;
      });
    };

    inventory_service.get_taxlot_columns = function () {
      return inventory_service.get_taxlot_columns_for_org(user_service.get_organization().id);
    };

    inventory_service.get_taxlot_columns_for_org = function (org_id, only_used, display_units = true) {
      if (only_used === undefined) only_used = false;
      return $http.get('/api/v3/columns/', {
        params: {
          inventory_type: 'taxlot',
          organization_id: org_id,
          only_used: only_used,
          display_units: display_units
        }
      }).then(function (response) {
        // Remove empty columns
        var columns = _.filter(response.data.columns, function (col) {
          return !_.isEmpty(col.name);
        });

        // Rename display_name to displayName (ui-grid compatibility)
        columns = _.map(columns, function (col) {
          return _.mapKeys(col, function (value, key) {
            return key === 'display_name' ? 'displayName' : key;
          });
        });

        // Remove _orig columns
        // if (flippers.is_active('release:orig_columns')) {
        //   _.remove(columns, function (col) {
        //     return /_orig/.test(col.name);
        //   });
        // }

        // Check for problems
        var duplicates = _.filter(_.map(columns, 'name'), function (value, index, iteratee) {
          return _.includes(iteratee, value, index + 1);
        });
        if (duplicates.length) {
          $log.error('Duplicate tax lot column names detected:', duplicates);
        }

        return columns;
      });
    };

    inventory_service.get_mappable_taxlot_columns = function () {
      return $http.get('/api/v3/columns/mappable/', {
        params: {
          organization_id: user_service.get_organization().id,
          inventory_type: 'taxlot',
        }
      }).then(function (response) {
        // Remove empty columns
        var columns = _.filter(response.data.columns, function (col) {
          return !_.isEmpty(col.name);
        });

        // Rename display_name to displayName (ui-grid compatibility)
        columns = _.map(columns, function (col) {
          return _.mapKeys(col, function (value, key) {
            return key === 'display_name' ? 'displayName' : key;
          });
        });

        // Remove _orig columns
        // if (flippers.is_active('release:orig_columns')) {
        //   _.remove(columns, function (col) {
        //     return /_orig/.test(col.name);
        //   });
        // }

        // Check for problems
        var duplicates = _.filter(_.map(columns, 'name'), function (value, index, iteratee) {
          return _.includes(iteratee, value, index + 1);
        });
        if (duplicates.length) {
          $log.error('Duplicate tax lot column names detected:', duplicates);
        }

        return columns;
      });
    };

    // https://regexr.com/3j1tq
    var combinedRegex = /^(!?)=\s*(-?\d+(?:\\\.\d+)?)$|^(!?)=?\s*"((?:[^"]|\\")*)"$|^(<=?|>=?)\s*(-?\d+(?:\\\.\d+)?)$/;
    inventory_service.combinedFilter = function () {
      return {
        condition: function (searchTerm, cellValue) {
          // console.log('searchTerm:', typeof searchTerm, `|${searchTerm}|`);
          // console.log('cellValue:', typeof cellValue, `|${cellValue}|`);
          if (_.isNil(cellValue)) cellValue = '';
          if (_.isString(cellValue)) cellValue = _.trim(cellValue);
          var match = true;
          var searchTerms = _.map(_.split(searchTerm, ','), _.trim);
          // Loop over multiple comma-separated filters
          _.forEach(searchTerms, function (search) {
            var operator, regex, value;
            var filterData = search.match(combinedRegex);
            if (filterData) {
              if (!_.isUndefined(filterData[2])) {
                // Numeric Equality
                operator = filterData[1];
                value = Number(filterData[2].replace('\\.', '.'));
                if (operator === '!') {
                  // Not equal
                  match = cellValue != value;
                } else {
                  // Equal
                  match = cellValue == value;
                }
                return match;
              } else if (!_.isUndefined(filterData[4])) {
                // Text Equality
                operator = filterData[3];
                value = filterData[4];
                regex = new RegExp('^' + value + '$');
                if (operator === '!') {
                  // Not equal
                  match = !regex.test(cellValue);
                } else {
                  // Equal
                  match = regex.test(cellValue);
                }
                return match;
              } else {
                // Numeric Comparison
                if (cellValue === '') {
                  match = false;
                  return match;
                }
                operator = filterData[5];
                value = Number(filterData[6].replace('\\.', '.'));
                switch (operator) {
                  case '<':
                    match = cellValue < value;
                    break;
                  case '<=':
                    match = cellValue <= value;
                    break;
                  case '>':
                    match = cellValue > value;
                    break;
                  case '>=':
                    match = cellValue >= value;
                    break;
                }
                return match;
              }
            } else {
              // Case-insensitive Contains
              regex = new RegExp(search, 'i');
              match = regex.test(cellValue);
              return match;
            }
          });
          return match;
        }
      };
    };

    // https://regexr.com/50ok6
    var dateRegex = /^(!?=?)\s*(""|\d{4}(?:-\d{2}(?:-\d{2})?)?)$|^(<=?|>=?)\s*(\d{4}(?:-\d{2}(?:-\d{2})?)?)$/;
    inventory_service.dateFilter = function () {
      return {
        condition: function (searchTerm, cellValue) {
          // console.log('searchTerm:', typeof searchTerm, `|${searchTerm}|`);
          // console.log('cellValue:', typeof cellValue, `|${cellValue}|`);
          if (_.isNil(cellValue)) cellValue = '';
          if (_.isString(cellValue)) cellValue = _.trim(cellValue);
          var match = true;
          var d = moment.utc(cellValue);
          var cellDate = d.valueOf();
          var cellYMD = {
            y: d.year(),
            m: d.month() + 1,
            d: d.date()
          };
          var searchTerms = _.map(_.split(_.replace(searchTerm, /\\-/g, '-'), ','), _.trim);
          // Loop over multiple comma-separated filters
          _.forEach(searchTerms, function (search) {
            var filterData = search.match(dateRegex);
            if (filterData) {
              var operator, value, v, ymd;
              if (!_.isUndefined(filterData[2])) {
                // Equality condition
                operator = filterData[1];
                value = filterData[2];

                if (value === '""') {
                  match = _.startsWith(operator, '!') ? !_.isEmpty(cellValue) : _.isEmpty(cellValue);
                  return match;
                }

                v = value.match(/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/);
                ymd = {
                  y: _.parseInt(v[1]),
                  m: _.parseInt(v[2]),
                  d: _.parseInt(v[3])
                };
                if (_.startsWith(operator, '!')) {
                  // Not equal
                  match = cellYMD.y !== ymd.y || (!_.isNaN(ymd.m) && cellYMD.y === ymd.y && cellYMD.m !== ymd.m) || (!_.isNaN(ymd.m) && !_.isNaN(ymd.d) && cellYMD.y === ymd.y && cellYMD.m === ymd.m && cellYMD.d !== ymd.d);
                  return match;
                } else {
                  // Equal
                  match = cellYMD.y === ymd.y && (_.isNaN(ymd.m) || cellYMD.m === ymd.m) && (_.isNaN(ymd.d) || cellYMD.d === ymd.d);
                  return match;
                }
              } else {
                // Range condition
                if (_.isNil(cellValue)) {
                  match = false;
                  return match;
                }

                operator = filterData[3];
                switch (operator) {
                  case '<':
                    value = Date.parse(filterData[4] + ' 00:00:00 GMT');
                    match = cellDate < value;
                    return match;
                  case '<=':
                    value = filterData[4];
                    v = value.match(/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/);
                    ymd = {
                      y: _.parseInt(v[1]),
                      m: _.parseInt(v[2]),
                      d: _.parseInt(v[3])
                    };


                    if (filterData[4].length === 10) {
                      // Add a day, subtract a millisecond
                      value = Date.parse(filterData[4] + ' 00:00:00 GMT') + 86399999;
                    } else if (filterData[4].length === 7) {
                      // Add a month, subtract a millisecond
                      if (ymd.m === 12) {
                        d = (ymd.y + 1) + '-01';
                      } else {
                        d = ymd.y + '-' + _.padStart(ymd.m + 1, 2, '0');
                      }
                      value = Date.parse(d + ' 00:00:00 GMT') - 1;
                    } else if (filterData[4].length === 4) {
                      // Add a year, subtract a millisecond
                      value = Date.parse((ymd.y + 1) + ' 00:00:00 GMT') - 1;
                    }

                    match = cellDate <= value;
                    return match;
                  case '>':
                    value = filterData[4];
                    v = value.match(/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/);
                    ymd = {
                      y: _.parseInt(v[1]),
                      m: _.parseInt(v[2]),
                      d: _.parseInt(v[3])
                    };

                    if (filterData[4].length === 10) {
                      // Add a day, subtract a millisecond
                      value = Date.parse(filterData[4] + ' 00:00:00 GMT') + 86399999;
                    } else if (filterData[4].length === 7) {
                      // Add a month, subtract a millisecond
                      if (ymd.m === 12) {
                        d = (ymd.y + 1) + '-01';
                      } else {
                        d = ymd.y + '-' + _.padStart(ymd.m + 1, 2, '0');
                      }
                      value = Date.parse(d + ' 00:00:00 GMT') - 1;
                    } else if (filterData[4].length === 4) {
                      // Add a year, subtract a millisecond
                      value = Date.parse((ymd.y + 1) + ' 00:00:00 GMT') - 1;
                    }

                    match = cellDate > value;
                    return match;
                  case '>=':
                    value = Date.parse(filterData[4] + ' 00:00:00 GMT');
                    match = cellDate >= value;
                    return match;
                }
              }
            } else {
              match = false;
              return match;
            }
          });
          return match;
        }
      };
    };

    inventory_service.saveSelectedLabels = function (key, ids) {
      key += '.' + user_service.get_organization().id;
      localStorage.setItem(key, JSON.stringify(ids));
    };

    inventory_service.loadSelectedLabels = function (key) {
      key += '.' + user_service.get_organization().id;
      return JSON.parse(localStorage.getItem(key)) || [];
    };

    // Save non-empty sort/filter states
    inventory_service.saveGridSettings = function (key, settings) {
      key += '.' + user_service.get_organization().id;
      localStorage.setItem(key, JSON.stringify(settings));
    };

    inventory_service.loadGridSettings = function (key) {
      key += '.' + user_service.get_organization().id;
      return localStorage.getItem(key);
    };

    inventory_service.saveMatchesPerPage = function (matchesPerPage) {
      var key = 'matchesPerPage.' + user_service.get_organization().id;
      localStorage.setItem(key, matchesPerPage);
    };

    inventory_service.loadMatchesPerPage = function () {
      var key = 'matchesPerPage.' + user_service.get_organization().id;
      return _.parseInt(localStorage.getItem(key)) || 25;
    };

    inventory_service.saveDetailMatchesPerPage = function (matchesPerPage) {
      var key = 'detailMatchesPerPage.' + user_service.get_organization().id;
      localStorage.setItem(key, matchesPerPage);
    };

    inventory_service.loadDetailMatchesPerPage = function () {
      var key = 'detailMatchesPerPage.' + user_service.get_organization().id;
      return _.parseInt(localStorage.getItem(key)) || 25;
    };

    // A list of which fields have date values. This will be used by controller
    // to format date value correctly. Ideally at some point this should be gathered
    // from the server rather than hardcoded here.

    // TODO: Identify Tax Lot specific values that have dates.
    inventory_service.property_state_date_columns = [
      'generation_date',
      'release_date',
      'recent_sale_date',
      'year_ending',
      'record_created',
      'record_modified',
      'record_year_ending'
    ];

    // TODO: Identify Tax Lot specific values that have dates.
    inventory_service.taxlot_state_date_columns = [
      'generation_date',
      'release_date',
      'recent_sale_date',
      'year_ending',
      'record_created',
      'record_modified',
      'record_year_ending'
    ];

    inventory_service.reorderSettings = function (columns) {
      var pinned = _.remove(columns, 'pinnedLeft');
      var selected = _.remove(columns, 'visible');
      return pinned.concat(selected).concat(columns);
    };

    inventory_service.search_matching_inventory = function (import_file_id) {
      return $http.post('/api/v3/import_files/' + import_file_id + '/mapping_results/', undefined, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    inventory_service.get_used_columns = function (org_id) {
      return $http.get('/api/v3/columns/', {
        params: {
          organization_id: org_id,
          only_used: true
        }
      }).then(function (response) {
        return response.data;
      });
    };

    inventory_service.get_matching_and_geocoding_results = function (import_file_id) {
      return $http.get('/api/v3/import_files/' + import_file_id + '/matching_and_geocoding_results/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    inventory_service.get_column_list_profiles = function (profile_location, inventory_type) {
      return $http.get('/api/v3/column_list_profiles/', {
        params: {
          organization_id: user_service.get_organization().id,
          inventory_type: inventory_type,
          profile_location: profile_location
        }
      }).then(function (response) {
        var profiles = response.data.data.sort(function (a, b) {
          return naturalSort(a.name, b.name);
        });

        _.forEach(profiles, function (profile) {
          // Remove exact duplicates - this shouldn't be necessary, but it has occurred and will avoid errors and cleanup the database at the same time
          profile.columns = _.uniqWith(profile.columns, _.isEqual);

          profile.columns = _.sortBy(profile.columns, ['order', 'column_name']);
        });

        return profiles;
      });
    };

    inventory_service.new_column_list_profile = function (data) {
      return $http.post('/api/v3/column_list_profiles/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    inventory_service.update_column_list_profile = function (id, data) {
      if (id === null) {
        Notification.error('This settings profile is protected from modifications');
        return $q.reject();
      }
      return $http.put('/api/v3/column_list_profiles/' + id + '/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    inventory_service.remove_column_list_profile = function (id) {
      if (id === null) {
        Notification.error('This settings profile is protected from modifications');
        return $q.reject();
      }
      return $http.delete('/api/v3/column_list_profiles/' + id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      });
    };

    return inventory_service;

  }]);
