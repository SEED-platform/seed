/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// inventory services
angular.module('BE.seed.service.inventory', []).factory('inventory_service', [
  '$http',
  '$log',
  'urls',
  'user_service',
  'cycle_service',
  'spinner_utility',
  function ($http, $log, urls, user_service, cycle_service, spinner_utility) {

    var inventory_service = {
      total_properties_for_user: 0,
      total_taxlots_for_user: 0
    };

    inventory_service.get_properties = function (page, per_page, cycle, columns) {

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
          inventory_service.save_last_cycle(cycle.id);
        } else if (_.includes(validCycleIds, lastCycleId)) {
          params.cycle = lastCycleId;
        }

        spinner_utility.show();

        return $http.post('/api/v2/properties/filter/', {
          // Ensure that the required meta fields are included
          columns: _.uniq(columns.concat(['property_state_id', 'taxlot_state_id', 'property_view_id', 'taxlot_view_id']))
        }, {
          params: params
        }).then(function (response) {
          return response.data;
        }).finally(function () {
          spinner_utility.hide();
        });
      }).catch(_.constant('Error fetching cycles'));
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

    inventory_service.get_property = function (property_id, cycle_id) {
      // Error checks
      if (_.isNil(property_id)) {
        $log.error('#inventory_service.get_property(): property_id is undefined');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(cycle_id)) {
        $log.error('#inventory_service.get_property(): cycle_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.get('/api/v2/properties/' + property_id + '/', {
        params: {
          cycle_id: cycle_id,
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    /** Update Property State for a specified property, cycle, and organization.
     *
     * @param property_id         Property ID of the property
     * @param cycle_id            Cycle ID for the cycle
     * @param state               A Property state object, which should include key/values for
     *                              all state values
     *
     * @returns {Promise}
     */
    inventory_service.update_property = function (property_id, cycle_id, state) {
      // Error checks
      if (_.isNil(property_id)) {
        $log.error('#inventory_service.update_property(): property_id is undefined');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(cycle_id)) {
        $log.error('#inventory_service.update_property(): cycle_id is undefined');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(state)) {
        $log.error('#inventory_service.update_property(): state is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.put('/api/v2/properties/' + property_id + '/', {
        state: state
      }, {
        params: {
          cycle_id: cycle_id,
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };


    inventory_service.delete_property_states = function (ids) {
      return $http.delete('/api/v2/properties/batch_delete/', {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: {
          organization_id: user_service.get_organization().id,
          selected: ids
        }
      });
    };


    inventory_service.delete_taxlot_states = function (ids) {
      return $http.delete('/api/v2/taxlots/batch_delete/', {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        data: {
          organization_id: user_service.get_organization().id,
          selected: ids
        }
      });
    };


    inventory_service.get_taxlots = function (page, per_page, cycle, columns) {
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
          inventory_service.save_last_cycle(cycle.id);
        } else if (_.includes(validCycleIds, lastCycleId)) {
          params.cycle = lastCycleId;
        }

        spinner_utility.show();
        return $http.post('/api/v2/taxlots/filter/', {
          // Ensure that the required meta fields are included
          columns: _.uniq(columns.concat(['property_state_id', 'taxlot_state_id', 'property_view_id', 'taxlot_view_id']))
        }, {
          params: params
        }).then(function (response) {
          return response.data;
        }).finally(function () {
          spinner_utility.hide();
        });
      }).catch(_.constant('Error fetching cycles'));
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


    inventory_service.get_taxlot = function (taxlot_id, cycle_id) {

      // Error checks
      if (_.isNil(taxlot_id)) {
        $log.error('#inventory_service.get_taxlot(): null taxlot_id parameter');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(cycle_id)) {
        $log.error('#inventory_service.get_taxlot(): null cycle_id parameter');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.get('/api/v2/taxlots/' + taxlot_id + '/', {
        params: {
          cycle_id: cycle_id,
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };


    /** Update Tax Lot State for a specified Tax Lot, cycle, and organization.
     *
     * @param taxlot_id          Tax Lot ID of the tax lot
     * @param cycle_id            Cycle ID for the cycle
     * @param state               A Tax Lot state object, which should include key/values for
     *                              all state values
     *
     * @returns {Promise}
     */
    inventory_service.update_taxlot = function (taxlot_id, cycle_id, state) {
      // Error checks
      if (_.isNil(taxlot_id)) {
        $log.error('#inventory_service.update_taxlot(): taxlot_id is undefined');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(cycle_id)) {
        $log.error('#inventory_service.update_taxlot(): cycle_id is undefined');
        throw new Error('Invalid Parameter');
      }
      if (_.isNil(state)) {
        $log.error('#inventory_service.update_taxlot(): state is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http.put('/api/v2/taxlots/' + taxlot_id + '/', {
        state: state
      }, {
        params: {
          cycle_id: cycle_id,
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


    inventory_service.get_property_columns = function () {
      return $http.get('/api/v2/properties/columns/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        // Remove empty columns
        return _.filter(response.data.columns, function (col) {
          return !_.isEmpty(col.name);
        });
      });
    };


    inventory_service.get_taxlot_columns = function () {
      return $http.get('/api/v2/taxlots/columns/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        // Remove empty columns
        return _.filter(response.data.columns, function (col) {
          return !_.isEmpty(col.name);
        });
      });
    };

    var textRegex = /^(!?)"(([^"]|\\")*)"$/;
    inventory_service.textFilter = function () {
      return {
        condition: function (searchTerm, cellValue) {
          if (_.isNil(cellValue)) cellValue = '';
          var filterData = searchTerm.match(textRegex);
          var regex;
          if (filterData) {
            var inverse = filterData[1] == '!';
            var value = filterData[2];
            regex = new RegExp('^' + value + '$');
            return inverse ? !regex.test(cellValue) : regex.test(cellValue);
          } else {
            regex = new RegExp(searchTerm, 'i');
            return regex.test(cellValue);
          }
        }
      };
    };


    var numRegex = /^(==?|!=?|<>)?\s*(null|-?\d+)|(<=?|>=?)\s*(-?\d+)$/;
    inventory_service.numFilter = function () {
      return {
        condition: function (searchTerm, cellValue) {
          var match = true;
          var searchTerms = _.map(_.split(searchTerm, ','), _.trim);
          _.forEach(searchTerms, function (search) {
            var filterData = search.match(numRegex);
            if (filterData) {
              var operator, value;
              if (!_.isUndefined(filterData[2])) {
                // Equality condition
                operator = filterData[1];
                value = filterData[2];
                if (_.isUndefined(operator) || _.startsWith(operator, '=')) {
                  // Equal
                  match = (value == 'null') ? (_.isNil(cellValue)) : (cellValue == value);
                  return match;
                } else {
                  // Not equal
                  match = (value == 'null') ? (!_.isNil(cellValue)) : (cellValue != value);
                  return match;
                }
              } else {
                // Range condition
                if (_.isNil(cellValue)) {
                  match = false;
                  return match;
                }

                operator = filterData[3];
                value = Number(filterData[4]);
                switch (operator) {
                  case '<':
                    match = cellValue < value;
                    return match;
                  case '<=':
                    match = cellValue <= value;
                    return match;
                  case '>':
                    match = cellValue > value;
                    return match;
                  case '>=':
                    match = cellValue >= value;
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

    inventory_service.saveSettings = function (key, columns) {
      key += '.' + user_service.get_organization().id;
      var toSave = inventory_service.reorderSettings(_.map(columns, function (col) {
        return _.pick(col, ['name', 'pinnedLeft', 'related', 'visible']);
      }));
      localStorage.setItem(key, JSON.stringify(toSave));
    };

    inventory_service.loadSettings = function (key, columns) {
      key += '.' + user_service.get_organization().id;

      var isDetailSetting = key.match(/^grid\.(properties|taxlots)\.detail\.\d+$/);

      // Hide extra data columns by default
      _.forEach(columns, function (col) {
        col.visible = !col.extraData;
      });

      var localColumns = localStorage.getItem(key);
      if (!_.isNull(localColumns)) {
        var existingColumnNames = _.map(columns, 'name');
        localColumns = JSON.parse(localColumns);

        // Remove deprecated columns missing 'related' field
        // NOT FOR DETAIL SETTINGS
        if (!isDetailSetting) {
          _.remove(localColumns, function (col) {
            return !_.has(col, 'related');
          });
        }

        // Remove nonexistent columns
        _.remove(localColumns, function (col) {
          return !_.includes(existingColumnNames, col.name);
        });
        // Use saved column settings with original data as defaults
        localColumns = _.map(localColumns, function (col) {
          if (isDetailSetting) return _.defaults(col, _.remove(columns, {name: col.name})[0]);
          else return _.defaults(col, _.remove(columns, {name: col.name, related: col.related})[0]);
        });
        // If no columns are visible, reset visibility only
        if (!_.find(localColumns, 'visible')) {
          _.forEach(localColumns, function (col) {
            col.visible = !col.extraData;
          });
        }
        return inventory_service.reorderSettings(localColumns.concat(columns));
      } else {
        return inventory_service.reorderSettings(columns);
      }
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

    inventory_service.removeSettings = function (key) {
      key += '.' + user_service.get_organization().id;
      localStorage.removeItem(key);
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

    inventory_service.search_matching_inventory = function (import_file_id, options) {
      spinner_utility.show();
      return $http.post('/api/v2/import_files/' + import_file_id + '/filtered_mapping_results/', options, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      }).finally(function () {
        spinner_utility.hide();
      });
    };

    inventory_service.get_columns = function (all_fields) {
      all_fields = all_fields || '';
      return $http.get('/app/get_columns/', {
        params: {
          all_fields: all_fields,
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    inventory_service.get_matching_results = function (import_file_id) {
      return $http.get('/api/v2/import_files/' + import_file_id + '/matching_results/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    return inventory_service;

  }]);
