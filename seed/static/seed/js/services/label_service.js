/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.label', []).factory('label_service', [
  '$http',
  '$log',
  'user_service',
  ($http, $log, user_service) => {
    /** Label Service:
       --------------------------------------------------
       Provides methods to CRUD labels on the server
       as well as apply and remove labels to properties.

       Note: This is the first service to use proper REST verbs and REST-based
       server APIs (provided by django-rest-framework).
       If this approach works well, the hope is to refactor all Angular services
       to use REST verbs and APIs.
       */

    /** Returns an array of labels.

       @param {array} selected                 An array of properties ids corresponding to
       selected properties (should be empty if
       select_all_checkbox is true).
       @param {object} search_params           A reference to the Search object, which
       includes properties for active filters.

       Returned label objects should have the following properties,
       with 'text' and 'color' properties assigned locally.

       id {integer}            The id of the label.
       name {string}           The text that appears in the label.
       text {string}           Same as name, needed for ngTagsInput control.
       color {string}          The text description of the label's color (e.g., 'blue').
       label {string}          The css class, usually in bootstrap, used to generate
       the color style (poorly named, needs refactoring).
       is_applied {boolean}    If a search object was passed in, this boolean
       indicates if properties in the current filtered
       set have this label.

       For example...
       [{
         id: 1,
         name: "test1",
         color: "blue",
         label: "primary",
         text: "test1",
         is_applied : true
       }]
       */

    const lookup_colors = {
      red: 'danger',
      gray: 'default',
      orange: 'warning',
      green: 'success',
      blue: 'primary',
      'light blue': 'info'
    };

    /**
     * Convert color names to bootstrap labels
     * @param {'red' | 'gray' | 'orange' | 'green' | 'blue' | 'light blue'} color
     * @returns {'danger' | 'default' | 'warning' | 'success' | 'primary' | 'info'}
     */
    const lookup_label = (color) => lookup_colors[color] ?? lookup_colors.gray;

    /**
     * Add a few properties to the label object so that it works well with UI components.
     * @param {object} label
     */
    const map_label = (label) => ({
      ...label,
      // add bootstrap label class names
      label: lookup_label(label.color),
      // create 'text' property needed for ngTagsInput control
      text: label.name
    });

    const map_labels = (response) => response.data.map(map_label);

    function get_labels_for_org(org_id, inventory_type, filter_ids, cycle_id) {
      const params = {
        organization_id: org_id
      };

      if (inventory_type == null) {
        return $http.get('/api/v3/labels/', { params }).then(map_labels);
      }

      let endpoint = null;
      const body = { selected: filter_ids };
      if (inventory_type === 'properties') {
        endpoint = 'properties/labels';
      } else if (inventory_type === 'taxlots') {
        endpoint = 'taxlots/labels';
      } else {
        throw Error(`Invalid inventory_type "${inventory_type}". Expecting properties or taxlots`);
      }

      return $http
        .post(`/api/v3/${endpoint}/`, body, {
          params: {
            ...params,
            cycle_id
          }
        })
        .then(map_labels);
    }

    // Passing no arguments will return all labels, but no information about what properties/taxlots they're applied to
    // Passing an inventory type will return all labels and the corresponding inventory type they're applied to
    // Passing an inventory type and filter_ids will return all labels but limited to only the selected properties/taxlots
    // Passing cycle_id will restrict is_applied ids to only those in the specified cycle
    const get_labels = (inventory_type, filter_ids, cycle_id) => get_labels_for_org(user_service.get_organization().id, inventory_type, filter_ids, cycle_id);

    /*  Add a label to an organization's list of labels

       @param {object} label       Label object to use for creating label on server.

       @return {object}            Returns a promise object which will resolve
       with either a success if the label was created
       on the server, or an error if the label could not be
       created on the server.

       Return object should also have a 'label' property assigned
       to the newly created label object.
       */
    const create_label_for_org = (org_id, label) => $http
      .post('/api/v3/labels/', label, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => map_label(response.data));

    const create_label = (label) => create_label_for_org(user_service.get_organization().id, label);

    /*  Update an existing a label in an organization

       @param {object} label   A label object with changed properties to update on server.
       The object must include property 'id' for label ID.

       @return {object}        Returns a promise object which will resolve
       with either a success if the label was updated,
       or an error if not.
       Return object will have a 'label' property assigned
       to the updated label object.
       */
    const update_label_for_org = (org_id, label) => $http
      .put(`/api/v3/labels/${label.id}/`, label, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => map_label(response.data));

    const update_label = (label) => update_label_for_org(user_service.get_organization().id, label);

    /*  Delete a label from the set of labels for an organization.

       @param {object} label       Label object to delete on server.
       Must include property 'id' for label ID.

       @return {object}            Returns a promise object which will resolve
       with either a success if the label was deleted,
       or an error if not.
       */
    const delete_label_for_org = (org_id, label) => $http
      .delete(`/api/v3/labels/${label.id}/`, {
        params: {
          organization_id: org_id
        }
      })
      .then((response) => response.data);

    const delete_label = (label) => delete_label_for_org(user_service.get_organization().id, label);

    /* FUNCTIONS FOR LABELS WITHIN PROPERTIES  */
    /* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */

    /**

       This method updates selected Properties with a group
       of "add" labels and a group of "remove" labels.

       @param {array} add_label_ids            An array of label ids to apply to selected properties.
       @param {array} remove_label_ids         An array of label ids to remove from selected properties.
       @param {array} selected                 An array of inventory ids corresponding to selected properties or taxlots
       (should be empty to get all).
       @return {object}                        A promise object that resolves server response
       (success or error).

       */
    const update_property_labels = (add_label_ids, remove_label_ids, selected) => $http
      .put(
        '/api/v3/labels_property/',
        {
          inventory_ids: selected,
          add_label_ids,
          remove_label_ids
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    /**
       This method updates selected Tax Lots with a group
       of "add" labels and a group of "remove" labels.

       @param {array} add_label_ids            An array of label ids to apply to selected properties.
       @param {array} remove_label_ids         An array of label ids to remove from selected properties.
       @param {array} selected                 An array of Tax Lot ids corresponding to selected Tax Lots
       (should be empty if select_all_checkbox is true).
       @return {object}                        A promise object that resolves server response
       (success or error).

       */
    const update_taxlot_labels = (add_label_ids, remove_label_ids, selected) => $http
      .put(
        '/api/v3/labels_taxlot/',
        {
          inventory_ids: selected,
          add_label_ids,
          remove_label_ids
        },
        {
          params: {
            organization_id: user_service.get_organization().id
          }
        }
      )
      .then((response) => response.data);

    /*  Gets the list of supported colors for labels, based on default bootstrap
       styles for labels. These are defined locally.

       @return {array}     List of label option objects.

       Label option objects have the following structure
       {
         'label' : {string} name of bootstrap class for label
         'color' : {string} text description of color
       }

       NOTE: At some point label colors should be defined on the server and not
       directly related to bootstrap colors. If we do stay with Bootstrap colors
       we should change the property names to something like 'bootstrap-class' and
       'color-description' (rather than 'label') to make them more clear.

       */
    const get_available_colors = () => [
      {
        label: 'success',
        color: 'green'
      },
      {
        label: 'danger',
        color: 'red'
      },
      {
        label: 'default',
        color: 'gray'
      },
      {
        label: 'warning',
        color: 'orange'
      },
      {
        label: 'info',
        color: 'light blue'
      },
      {
        label: 'primary',
        color: 'blue'
      }
    ];

    return {
      get_labels,
      get_labels_for_org,
      create_label,
      create_label_for_org,
      update_label,
      update_label_for_org,
      delete_label,
      delete_label_for_org,
      update_property_labels,
      update_taxlot_labels,
      get_available_colors,
      lookup_label
    };
  }
]);
