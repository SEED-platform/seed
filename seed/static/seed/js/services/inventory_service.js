/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
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
  ($http, $log, $q, urls, user_service, cycle_service, spinner_utility, naturalSort, Notification) => {
    const inventory_service = {
      total_properties_for_user: 0,
      total_taxlots_for_user: 0
    };

    const format_column_filters = (column_filters) => {
      // turn column filter objects into usable query parameters
      if (!column_filters) {
        return {};
      }

      const filters = {};
      for (const { name, operator, value } of column_filters) {
        filters[`${name}__${operator}`] = value;
      }

      return filters;
    };

    inventory_service.get_format_column_filters = format_column_filters;

    const format_column_sorts = (column_sorts) => {
      // turn column sort objects into usable query parameter
      if (!column_sorts) {
        return [];
      }

      const sorts = [];
      for (const { name, direction } of column_sorts) {
        const direction_operator = direction === 'desc' ? '-' : '';
        sorts.push(`${direction_operator}${name}`);
      }

      return { order_by: sorts };
    };

    inventory_service.get_properties = (
      page,
      per_page,
      cycle,
      profile_id,
      include_view_ids,
      exclude_view_ids,
      save_last_cycle = true,
      organization_id = null,
      include_related = true,
      column_filters = null,
      column_sorts = null,
      ids_only = null,
      shown_column_ids = null
    ) => {
      organization_id = organization_id == undefined ? user_service.get_organization().id : organization_id;

      const params = {
        organization_id,
        include_related,
        ids_only,
        shown_column_ids,
        ...format_column_sorts(column_sorts),
        ...format_column_filters(column_filters)
      };

      if (ids_only) {
        params.ids_only = true;
      } else {
        params.page = page;
        params.per_page = per_page || 999999999;
      }

      return cycle_service
        .get_cycles()
        .then((cycles) => {
          const validCycleIds = _.map(cycles.cycles, 'id');

          const lastCycleId = inventory_service.get_last_cycle();
          if (_.has(cycle, 'id')) {
            params.cycle = cycle.id;
            if (save_last_cycle === true) {
              inventory_service.save_last_cycle(cycle.id);
            }
          } else if (_.includes(validCycleIds, lastCycleId)) {
            params.cycle = lastCycleId;
          }

          return $http
            .post(
              '/api/v3/properties/filter/',
              {
                // Pass the specific ids if they exist
                include_view_ids,
                exclude_view_ids,
                // Pass the current profile (if one exists) to limit the column data that is returned
                profile_id
              },
              {
                params
              }
            )
            .then((response) => response.data);
        })
        .catch((response) => {
          if (response.data.message) {
            return response.data;
          }
          throw response;
        });
    };

    inventory_service.properties_cycle = (profile_id, cycle_ids) => $http
      .post('/api/v3/properties/filter_by_cycle/', {
        organization_id: user_service.get_organization().id,
        profile_id,
        cycle_ids
      })
      .then((response) => response.data);

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

    inventory_service.properties_meters_exist = (property_view_ids) => $http
      .post(
        '/api/v3/properties/meters_exist/',
        {
          property_view_ids
        },
        {
          params: { organization_id: user_service.get_organization().id }
        }
      )
      .then((response) => response.data);

    inventory_service.get_canonical_properties = (view_ids) => $http
      .post(
        '/api/v3/properties/get_canonical_properties/',
        { view_ids },
        {
          params: { organization_id: user_service.get_organization().id }
        }
      )
      .then((response) => response.data)
      .catch((response) => response.data);

    inventory_service.get_property = (view_id) => {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_property(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http
        .get(`/api/v3/properties/${view_id}/`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    inventory_service.get_property_views = (organization_id, property_id) => $http
      .get('/api/v3/property_views/', {
        params: {
          organization_id,
          property: property_id
        }
      })
      .then((response) => response.data);

    inventory_service.get_taxlot_views = (organization_id, taxlot_id) => $http
      .get('/api/v3/taxlot_views/', {
        params: {
          organization_id,
          taxlot: taxlot_id
        }
      })
      .then((response) => response.data);

    inventory_service.delete_inventory_document = (view_id, file_id) => $http
      .delete(`/api/v3/properties/${view_id}/delete_inventory_document/`, {
        headers: {
          'Content-Type': 'application/json;charset=utf-8'
        },
        params: {
          organization_id: user_service.get_organization().id,
          file_id
        }
      })
      .then((response) => response.data);

    inventory_service.get_property_links = (view_id) => {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_property_links(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http
        .get(`/api/v3/properties/${view_id}/links/`, {
          params: { organization_id: user_service.get_organization().id }
        })
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    inventory_service.property_match_merge_link = (view_id) => {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.property_match_merge_link(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http
        .post(
          `/api/v3/properties/${view_id}/match_merge_link/`,
          {},
          {
            params: { organization_id: user_service.get_organization().id }
          }
        )
        .then((response) => response.data)
        .finally(() => {
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
    inventory_service.update_property = (view_id, state) => {
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

      return $http
        .put(
          `/api/v3/properties/${view_id}/`,
          {
            state
          },
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    /** Update Salesforce for specified property views and organization
     *
     * @param property_view_ids        List of Property View IDs
     *
     * @returns {Promise}
     */
    inventory_service.update_salesforce = (property_view_ids) => {
      spinner_utility.show();
      return $http
        .post(
          '/api/v3/properties/update_salesforce/',
          {
            property_view_ids
          },
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    inventory_service.delete_property_states = (property_view_ids) => $http.delete('/api/v3/properties/batch_delete/', {
      headers: {
        'Content-Type': 'application/json;charset=utf-8'
      },
      data: { property_view_ids },
      params: { organization_id: user_service.get_organization().id }
    });

    inventory_service.delete_taxlot_states = (taxlot_view_ids) => $http.delete('/api/v3/taxlots/batch_delete/', {
      headers: {
        'Content-Type': 'application/json;charset=utf-8'
      },
      data: { taxlot_view_ids },
      params: { organization_id: user_service.get_organization().id }
    });

    inventory_service.get_taxlots = (
      page,
      per_page,
      cycle,
      profile_id,
      include_view_ids,
      exclude_view_ids,
      save_last_cycle = true,
      organization_id = null,
      include_related = true,
      column_filters = null,
      column_sorts = null,
      ids_only = null,
      shown_column_ids = null
    ) => {
      organization_id = organization_id == undefined ? user_service.get_organization().id : organization_id;

      const params = {
        organization_id,
        include_related,
        ids_only,
        shown_column_ids,
        ...format_column_sorts(column_sorts),
        ...format_column_filters(column_filters)
      };

      if (ids_only) {
        params.ids_only = true;
      } else {
        params.page = page;
        params.per_page = per_page || 999999999;
      }

      return cycle_service
        .get_cycles()
        .then((cycles) => {
          const validCycleIds = _.map(cycles.cycles, 'id');

          const lastCycleId = inventory_service.get_last_cycle();
          if (cycle) {
            params.cycle = cycle.id;
            if (save_last_cycle === true) {
              inventory_service.save_last_cycle(cycle.id);
            }
          } else if (_.includes(validCycleIds, lastCycleId)) {
            params.cycle = lastCycleId;
          }

          return $http
            .post(
              '/api/v3/taxlots/filter/',
              {
                // Pass the specific ids if they exist
                include_view_ids,
                exclude_view_ids,
                // Pass the current profile (if one exists) to limit the column data that is returned
                profile_id
              },
              {
                params
              }
            )
            .then((response) => response.data);
        })
        .catch((response) => {
          if (response.data.message) {
            return response.data;
          }
          throw response;
        });
    };

    inventory_service.taxlots_cycle = (profile_id, cycle_ids) => $http
      .post('/api/v3/taxlots/filter_by_cycle/', {
        organization_id: user_service.get_organization().id,
        profile_id,
        cycle_ids
      })
      .then((response) => response.data);

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

    inventory_service.get_taxlot = (view_id) => {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_taxlot(): null view_id parameter');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http
        .get(`/api/v3/taxlots/${view_id}/`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    inventory_service.get_taxlot_links = (view_id) => {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.get_taxlot_links(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http
        .get(`/api/v3/taxlots/${view_id}/links/`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    inventory_service.taxlot_match_merge_link = (view_id) => {
      // Error checks
      if (_.isNil(view_id)) {
        $log.error('#inventory_service.taxlot_match_merge_link(): view_id is undefined');
        throw new Error('Invalid Parameter');
      }

      spinner_utility.show();
      return $http
        .post(
          `/api/v3/taxlots/${view_id}/match_merge_link/`,
          {},
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
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
    inventory_service.update_taxlot = (view_id, state) => {
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
      return $http
        .put(
          `/api/v3/taxlots/${view_id}/`,
          {
            state
          },
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    inventory_service.get_last_cycle = () => {
      const organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('cycles')) || {})[organization_id];
    };

    inventory_service.save_last_cycle = (pk, organization_id = null) => {
      organization_id = organization_id == undefined ? user_service.get_organization().id : organization_id;
      const cycles = JSON.parse(localStorage.getItem('cycles')) || {};
      cycles[organization_id] = _.toInteger(pk);
      localStorage.setItem('cycles', JSON.stringify(cycles));
    };

    inventory_service.get_last_selected_cycles = () => {
      const organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('selected_cycles')) || {})[organization_id];
    };

    inventory_service.save_last_selected_cycles = (ids) => {
      const organization_id = user_service.get_organization().id;
      const selected_cycles = JSON.parse(localStorage.getItem('selected_cycles')) || {};
      selected_cycles[organization_id] = ids;
      localStorage.setItem('selected_cycles', JSON.stringify(selected_cycles));
    };

    inventory_service.get_last_profile = (key) => {
      const organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem(`profiles.${key}`)) || {})[organization_id];
    };

    inventory_service.save_last_profile = (pk, key) => {
      const organization_id = user_service.get_organization().id;
      const profiles = JSON.parse(localStorage.getItem(`profiles.${key}`)) || {};
      profiles[organization_id] = _.toInteger(pk);
      localStorage.setItem(`profiles.${key}`, JSON.stringify(profiles));
    };

    inventory_service.get_last_detail_profile = (key) => {
      const organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem(`detailProfiles.${key}`)) || {})[organization_id];
    };

    inventory_service.save_last_detail_profile = (pk, key) => {
      const organization_id = user_service.get_organization().id;
      const profiles = JSON.parse(localStorage.getItem(`detailProfiles.${key}`)) || {};
      profiles[organization_id] = _.toInteger(pk);
      localStorage.setItem(`detailProfiles.${key}`, JSON.stringify(profiles));
    };

    inventory_service.get_property_column_names_for_org = (org_id) => $http
      .get('/api/v3/columns/', {
        params: {
          inventory_type: 'property',
          organization_id: org_id,
          only_used: false,
          display_units: true
        }
      })
      .then((response) => {
        const property_columns = response.data.columns.filter((column) => column.table_name === 'PropertyState');
        return property_columns.map((a) => ({ column_name: a.column_name, display_name: a.display_name }));
      });

    inventory_service.get_property_column_names_and_ids_for_org = (org_id) => $http
      .get('/api/v3/columns/', {
        params: {
          inventory_type: 'property',
          organization_id: org_id,
          only_used: false,
          display_units: true
        }
      })
      .then((response) => {
        const property_columns = response.data.columns.filter((column) => column.table_name === 'PropertyState');
        return property_columns.map((a) => ({ column_name: a.column_name, display_name: a.display_name, id: a.id }));
      });

    inventory_service.get_taxlot_column_names_for_org = (org_id) => $http
      .get('/api/v3/columns/', {
        params: {
          inventory_type: 'taxlot',
          organization_id: org_id,
          only_used: false,
          display_units: true
        }
      })
      .then((response) => {
        const taxlot_columns = response.data.columns.filter((column) => column.table_name === 'TaxLotState');
        return taxlot_columns.map((a) => ({ column_name: a.column_name, display_name: taxlot_columns.find((x) => x.column_name === a.column_name).display_name }));
      });

    inventory_service.get_property_columns = () => inventory_service.get_property_columns_for_org(user_service.get_organization().id);

    inventory_service.get_property_columns_for_org = (org_id, only_used, display_units = true) => {
      if (only_used === undefined) only_used = false;
      return $http
        .get('/api/v3/columns/', {
          params: {
            inventory_type: 'property',
            organization_id: org_id,
            only_used,
            display_units
          }
        })
        .then((response) => {
          // Remove empty columns
          let columns = _.filter(response.data.columns, (col) => !_.isEmpty(col.name));

          // Rename display_name to displayName (ui-grid compatibility)
          columns = _.map(columns, (col) => _.mapKeys(col, (value, key) => (key === 'display_name' ? 'displayName' : key)));

          // Check for problems
          const duplicates = _.filter(_.map(columns, 'name'), (value, index, iteratee) => _.includes(iteratee, value, index + 1));
          if (duplicates.length) {
            $log.error('Duplicate property column names detected:', duplicates);
          }

          return columns;
        });
    };

    inventory_service.get_mappable_property_columns = () => $http
      .get('/api/v3/columns/mappable/', {
        params: {
          organization_id: user_service.get_organization().id,
          inventory_type: 'property'
        }
      })
      .then((response) => {
        // Remove empty columns
        let columns = _.filter(response.data.columns, (col) => !_.isEmpty(col.name));

        // Rename display_name to displayName (ui-grid compatibility)
        columns = _.map(columns, (col) => _.mapKeys(col, (value, key) => (key === 'display_name' ? 'displayName' : key)));

        // Check for problems
        const duplicates = _.filter(_.map(columns, 'name'), (value, index, iteratee) => _.includes(iteratee, value, index + 1));
        if (duplicates.length) {
          $log.error('Duplicate property column names detected:', duplicates);
        }

        return columns;
      });

    inventory_service.get_taxlot_columns = () => inventory_service.get_taxlot_columns_for_org(user_service.get_organization().id);

    inventory_service.get_taxlot_columns_for_org = (org_id, only_used, display_units = true) => {
      if (only_used === undefined) only_used = false;
      return $http
        .get('/api/v3/columns/', {
          params: {
            inventory_type: 'taxlot',
            organization_id: org_id,
            only_used,
            display_units
          }
        })
        .then((response) => {
          // Remove empty columns
          let columns = _.filter(response.data.columns, (col) => !_.isEmpty(col.name));

          // Rename display_name to displayName (ui-grid compatibility)
          columns = _.map(columns, (col) => _.mapKeys(col, (value, key) => (key === 'display_name' ? 'displayName' : key)));

          // Check for problems
          const duplicates = _.filter(_.map(columns, 'name'), (value, index, iteratee) => _.includes(iteratee, value, index + 1));
          if (duplicates.length) {
            $log.error('Duplicate tax lot column names detected:', duplicates);
          }

          return columns;
        });
    };

    inventory_service.get_mappable_taxlot_columns = () => $http
      .get('/api/v3/columns/mappable/', {
        params: {
          organization_id: user_service.get_organization().id,
          inventory_type: 'taxlot'
        }
      })
      .then((response) => {
        // Remove empty columns
        let columns = _.filter(response.data.columns, (col) => !_.isEmpty(col.name));

        // Rename display_name to displayName (ui-grid compatibility)
        columns = _.map(columns, (col) => _.mapKeys(col, (value, key) => (key === 'display_name' ? 'displayName' : key)));

        // Check for problems
        const duplicates = _.filter(_.map(columns, 'name'), (value, index, iteratee) => _.includes(iteratee, value, index + 1));
        if (duplicates.length) {
          $log.error('Duplicate tax lot column names detected:', duplicates);
        }

        return columns;
      });

    // https://regexr.com/3j1tq
    const combinedRegex = /^(!?)=\s*(-?\d+(?:\\\.\d+)?)$|^(!?)=?\s*"((?:[^"]|\\")*)"$|^(<=?|>=?)\s*(-?\d+(?:\\\.\d+)?)$/;
    inventory_service.combinedFilter = () => ({
      condition(searchTerm, cellValue) {
        // console.log('searchTerm:', typeof searchTerm, `|${searchTerm}|`);
        // console.log('cellValue:', typeof cellValue, `|${cellValue}|`);
        if (_.isNil(cellValue)) cellValue = '';
        if (_.isString(cellValue)) cellValue = _.trim(cellValue);
        let match = true;
        const searchTerms = _.map(_.split(searchTerm, ','), _.trim);
        // Loop over multiple comma-separated filters
        _.forEach(searchTerms, (search) => {
          let operator;
          let regex;
          let value;
          const filterData = search.match(combinedRegex);
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
            }
            if (!_.isUndefined(filterData[4])) {
              // Text Equality
              operator = filterData[3];
              value = filterData[4];
              regex = new RegExp(`^${value}$`);
              if (operator === '!') {
                // Not equal
                match = !regex.test(cellValue);
              } else {
                // Equal
                match = regex.test(cellValue);
              }
              return match;
            }
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
          // Case-insensitive Contains
          regex = new RegExp(search, 'i');
          match = regex.test(cellValue);
          return match;
        });
        return match;
      }
    });

    // https://regexr.com/50ok6
    const dateRegex = /^(!?=?)\s*(""|\d{4}(?:-\d{2}(?:-\d{2})?)?)$|^(<=?|>=?)\s*(\d{4}(?:-\d{2}(?:-\d{2})?)?)$/;
    inventory_service.dateFilter = () => ({
      condition(searchTerm, cellValue) {
        // console.log('searchTerm:', typeof searchTerm, `|${searchTerm}|`);
        // console.log('cellValue:', typeof cellValue, `|${cellValue}|`);
        if (_.isNil(cellValue)) cellValue = '';
        if (typeof cellValue === 'string') cellValue = _.trim(cellValue);
        let match = true;
        let d = moment.utc(cellValue);
        const cellDate = d.valueOf();
        const cellYMD = {
          y: d.year(),
          m: d.month() + 1,
          d: d.date()
        };
        const searchTerms = _.map(_.split(_.replace(searchTerm, /\\-/g, '-'), ','), _.trim);
        // Loop over multiple comma-separated filters
        _.forEach(searchTerms, (search) => {
          const filterData = search.match(dateRegex);
          if (filterData) {
            let operator;
            let value;
            let v;
            let ymd;
            if (!_.isUndefined(filterData[2])) {
              // Equality condition
              operator = filterData[1];
              value = filterData[2];

              if (value === '""') {
                match = operator.startsWith('!') ? !_.isEmpty(cellValue) : _.isEmpty(cellValue);
                return match;
              }

              v = value.match(/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/);
              ymd = {
                y: _.parseInt(v[1]),
                m: _.parseInt(v[2]),
                d: _.parseInt(v[3])
              };
              if (operator.startsWith('!')) {
                // Not equal
                match =
                  cellYMD.y !== ymd.y ||
                  (!_.isNaN(ymd.m) && cellYMD.y === ymd.y && cellYMD.m !== ymd.m) ||
                  (!_.isNaN(ymd.m) && !_.isNaN(ymd.d) && cellYMD.y === ymd.y && cellYMD.m === ymd.m && cellYMD.d !== ymd.d);
                return match;
              }
              // Equal
              match = cellYMD.y === ymd.y && (_.isNaN(ymd.m) || cellYMD.m === ymd.m) && (_.isNaN(ymd.d) || cellYMD.d === ymd.d);
              return match;
            }
            // Range condition
            if (_.isNil(cellValue)) {
              match = false;
              return match;
            }

            operator = filterData[3];
            switch (operator) {
              case '<':
                value = Date.parse(`${filterData[4]} 00:00:00 GMT`);
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
                  value = Date.parse(`${filterData[4]} 00:00:00 GMT`) + 86399999;
                } else if (filterData[4].length === 7) {
                  // Add a month, subtract a millisecond
                  if (ymd.m === 12) {
                    d = `${ymd.y + 1}-01`;
                  } else {
                    d = `${ymd.y}-${_.padStart(ymd.m + 1, 2, '0')}`;
                  }
                  value = Date.parse(`${d} 00:00:00 GMT`) - 1;
                } else if (filterData[4].length === 4) {
                  // Add a year, subtract a millisecond
                  value = Date.parse(`${ymd.y + 1} 00:00:00 GMT`) - 1;
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
                  value = Date.parse(`${filterData[4]} 00:00:00 GMT`) + 86399999;
                } else if (filterData[4].length === 7) {
                  // Add a month, subtract a millisecond
                  if (ymd.m === 12) {
                    d = `${ymd.y + 1}-01`;
                  } else {
                    d = `${ymd.y}-${_.padStart(ymd.m + 1, 2, '0')}`;
                  }
                  value = Date.parse(`${d} 00:00:00 GMT`) - 1;
                } else if (filterData[4].length === 4) {
                  // Add a year, subtract a millisecond
                  value = Date.parse(`${ymd.y + 1} 00:00:00 GMT`) - 1;
                }

                match = cellDate > value;
                return match;
              case '>=':
                value = Date.parse(`${filterData[4]} 00:00:00 GMT`);
                match = cellDate >= value;
                return match;
            }
          } else {
            match = false;
            return match;
          }
        });
        return match;
      }
    });

    inventory_service.saveSelectedLabels = (key, ids) => {
      key += `.${user_service.get_organization().id}`;
      localStorage.setItem(key, JSON.stringify(ids));
    };

    inventory_service.loadSelectedLabels = (key) => {
      key += `.${user_service.get_organization().id}`;
      return JSON.parse(localStorage.getItem(key)) || [];
    };

    // Save non-empty sort/filter states
    inventory_service.saveGridSettings = (key, settings) => {
      key += `.${user_service.get_organization().id}`;
      localStorage.setItem(key, JSON.stringify(settings));
    };

    inventory_service.loadGridSettings = (key) => {
      key += `.${user_service.get_organization().id}`;
      return localStorage.getItem(key);
    };

    inventory_service.saveMatchesPerPage = (matchesPerPage) => {
      const key = `matchesPerPage.${user_service.get_organization().id}`;
      localStorage.setItem(key, matchesPerPage);
    };

    inventory_service.loadMatchesPerPage = () => {
      const key = `matchesPerPage.${user_service.get_organization().id}`;
      return _.parseInt(localStorage.getItem(key)) || 25;
    };

    inventory_service.saveDetailMatchesPerPage = (matchesPerPage) => {
      const key = `detailMatchesPerPage.${user_service.get_organization().id}`;
      localStorage.setItem(key, matchesPerPage);
    };

    inventory_service.loadDetailMatchesPerPage = () => {
      const key = `detailMatchesPerPage.${user_service.get_organization().id}`;
      return _.parseInt(localStorage.getItem(key)) || 25;
    };

    // A list of which fields have date values. This will be used by controller
    // to format date value correctly. Ideally at some point this should be gathered
    // from the server rather than hardcoded here.

    // TODO: Identify Tax Lot specific values that have dates.
    inventory_service.property_state_date_columns = ['generation_date', 'release_date', 'recent_sale_date', 'year_ending', 'record_created', 'record_modified', 'record_year_ending'];

    // TODO: Identify Tax Lot specific values that have dates.
    inventory_service.taxlot_state_date_columns = ['generation_date', 'release_date', 'recent_sale_date', 'year_ending', 'record_created', 'record_modified', 'record_year_ending'];

    inventory_service.reorderSettings = (columns) => {
      const pinned = _.remove(columns, 'pinnedLeft');
      const selected = _.remove(columns, 'visible');
      return pinned.concat(selected).concat(columns);
    };

    inventory_service.search_matching_inventory = (import_file_id) => $http
      .post(`/api/v3/import_files/${import_file_id}/mapping_results/`, undefined, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    inventory_service.get_used_columns = (org_id) => $http
      .get('/api/v3/columns/', {
        params: {
          organization_id: org_id,
          only_used: true
        }
      })
      .then((response) => response.data);

    inventory_service.get_matching_and_geocoding_results = (import_file_id) => $http
      .get(`/api/v3/import_files/${import_file_id}/matching_and_geocoding_results/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data);

    inventory_service.get_column_list_profile = (id) => $http
      .get(`/api/v3/column_list_profiles/${id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data.data);

    inventory_service.get_column_list_profiles = (profile_location, inventory_type, brief = false) => $http
      .get('/api/v3/column_list_profiles/', {
        params: {
          organization_id: user_service.get_organization().id,
          inventory_type,
          profile_location,
          brief
        }
      })
      .then((response) => {
        const profiles = response.data.data.sort((a, b) => naturalSort(a.name, b.name));

        _.forEach(profiles, (profile) => {
          // Remove exact duplicates - this shouldn't be necessary, but it has occurred and will avoid errors and cleanup the database at the same time
          profile.columns = _.uniqWith(profile.columns, _.isEqual);

          profile.columns = _.sortBy(profile.columns, ['order', 'column_name']);
        });

        return profiles;
      });

    inventory_service.new_column_list_profile = (data) => $http
      .post('/api/v3/column_list_profiles/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data.data);

    inventory_service.update_column_list_profile = (id, data) => {
      if (id === null) {
        Notification.error('This settings profile is protected from modifications');
        return $q.reject();
      }
      return $http
        .put(`/api/v3/column_list_profiles/${id}/`, data, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data.data);
    };

    inventory_service.remove_column_list_profile = (id) => {
      if (id === null) {
        Notification.error('This settings profile is protected from modifications');
        return $q.reject();
      }
      return $http.delete(`/api/v3/column_list_profiles/${id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      });
    };

    inventory_service.set_update_to_now = (property_views, taxlot_views, progress_key) => $http.post('/api/v3/tax_lot_properties/set_update_to_now/', {
      property_views,
      taxlot_views,
      progress_key,
      organization_id: user_service.get_organization().id
    });

    inventory_service.start_set_update_to_now = () => $http.get('/api/v3/tax_lot_properties/start_set_update_to_now/', {
      params: {
        organization_id: user_service.get_organization().id
      }
    });

    inventory_service.get_portfolio_summary = (baseline_cycle_id) => {
      return $http.post('/api/v3/properties/portfolio_summary/', {
        organization_id: user_service.get_organization().id,
        baseline_cycle: baseline_cycle_id
      })
    }

    return inventory_service;
  }
]);
