angular.module('BE.seed.service.label',
    []).factory('label_service', ['$http',
                                    '$q',
                                    '$timeout',
                                    '$log',
                                    'user_service',
                                    'label_helper_service',
                        function ( $http,
                                    $q,
                                    $timeout,
                                    $log,
                                    user_service,
                                    label_helper_service
                                    ) {


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

        @param {array} selected_properties      An array of properties ids corresponding to
                                                selected properties (should be empty if
                                                select_all_checkbox is true).
        @param {boolean} select_all_checkbox    A boolean indicating whether user checked
                                                'Select all' checkbox.
        @param {object} search_params           A reference to the Search object, which
                                                includes properties for active filters.

        Returned label objects should have the following properties,
        with 'text' and 'color' properties assigned locally.

            id {integer}            The id of the label.
            name {string}           The text that appears in the label.
            text {string}           Same as name, needed for ngTagsInput control.
            color {string}          The text description of the label's color (e.g. 'blue').
            label {string}          The css class, usually in bootstrap, used to generate
                                    the color style (poorly named, needs refactoring).
            is_applied {boolean}    If a search object was passed in, this boolean
                                    indicates if properties in the current filtered
                                    set have this label.

        For example...
        [
            {
                id: 1,
                name: "test1",
                color: "blue",
                label: "primary",
                text: "test1",
                is_applied : true
            }
        ]
    */

    function get_labels(selected_properties, select_all_checkbox, search_params) {
        return get_labels_for_org(user_service.get_organization().id, selected_properties, select_all_checkbox, search_params);
    }

    function get_labels_for_org(org_id, selected_properties, select_all_checkbox, search_params) {
        var defer = $q.defer();

        var searchArgs = _.assignIn({
            inventory_type: 'property',
            selected_properties: selected_properties,
            select_all_checkbox: select_all_checkbox,
            organization_id: org_id
        }, search_params);

        $http({
            method: 'GET',
            url: window.BE.urls.label_list,
            params: searchArgs
        }).success(function(data, status, headers, config) {

            if (_.isEmpty(data.results)) {
                data.results = [];
            }

            data.results = _.map(data.results, update_label_w_local_props);
            defer.resolve(data);

        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /*  Add a label to an organization's list of labels

        @param {object} label       Label object to use for creating label on server.

        @return {object}            Returns a promise object which will resolve
                                    with either a success if the label was created
                                    on the server, or an error if the label could not be
                                    created on the server.

                                    Return object should also have a 'label' property assigned
                                    to the newly created label object.
    */
    function create_label(label){
        return create_label_for_org(user_service.get_organization().id, label);
    }

    function create_label_for_org(org_id, label){
        var defer = $q.defer();
        $http({
            method: 'POST',
            url: window.BE.urls.label_list,
            data: label,
            params: {
                organization_id: org_id
            }
        }).success(function(data, status, headers, config) {
            if(data){
                data = update_label_w_local_props(data);
            }
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /*  Update an existing a label in an organization

        @param {object} label   A label object with changed properties to update on server.
                                The object must include property 'id' for label ID.

        @return {object}        Returns a promise object which will resolve
                                with either a success if the label was updated,
                                or an error if not.
                                Return object will have a 'label' property assigned
                                to the updated label object.
    */
    function update_label(label){
        return update_label_for_org(user_service.get_organization().id, label);
    }

    function update_label_for_org(org_id, label){
        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: window.BE.urls.label_list + label.id + '/',
            data: label,
            params: {
                organization_id: org_id
            }
        }).success(function(data, status, headers, config) {
            if(data){
                data = update_label_w_local_props(data);
            }
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }

    /*  Delete a label from the set of labels for an organization.

        @param {object} label       Label object to delete on server.
                                    Must include property 'id' for label ID.

        @return {object}            Returns a promise object which will resolve
                                    with either a success if the label was deleted,
                                    or an error if not.
    */
    function delete_label(label){
        return delete_label_for_org(user_service.get_organization().id, label);
    }

    function delete_label_for_org(org_id, label){
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            url: window.BE.urls.label_list + label.id + '/',
            params: {
                organization_id: org_id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /* FUNCTIONS FOR LABELS WITHIN PROPERTIES  */
    /* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/

    /*

    This method updates selected Properties with a group
    of "add" labels and a group of "remove" labels.


    @param {array} add_label_ids            An array of label ids to apply to selected properties.
    @param {array} remove_label_ids         An array of label ids to remove from selected properties.
    @param {array} selected_properties      An array of Property ids corresponding to selected properties
                                            (should be empty if select_all_checkbox is true).
    @param {boolean} select_all_checkbox    A boolean indicating whether user checked 'Select all' checkbox.
    @param {object} search_params           A reference to the Search object, which includes
                                            properties for active filters.

    @return {object}                        A promise object that resolves server response
                                            (success or error).

    */
    function update_property_labels(add_label_ids, remove_label_ids, selected_properties, select_all_checkbox, search_params) {

        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: window.BE.urls.property_labels,
            params: _.assignIn({
                selected_properties: selected_properties,
                select_all_checkbox: select_all_checkbox,
                organization_id: user_service.get_organization().id
            }, search_params),
            data: {
                add_label_ids: add_label_ids,
                remove_label_ids: remove_label_ids
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /*
    This method updates selected Tax Lots with a group
    of "add" labels and a group of "remove" labels.


    @param {array} add_label_ids            An array of label ids to apply to selected properties.
    @param {array} remove_label_ids         An array of label ids to remove from selected properties.
    @param {array} selected_properties      An array of Tax Lot ids corresponding to selected Tax Lots
                                            (should be empty if select_all_checkbox is true).
    @param {boolean} select_all_checkbox    A boolean indicating whether user checked 'Select all' checkbox.
    @param {object} search_params           A reference to the Search object, which includes
                                            properties for active filters.

    @return {object}                        A promise object that resolves server response
                                            (success or error).

    */
    function update_taxlot_labels(add_label_ids, remove_label_ids, selected_taxlots, select_all_checkbox, search_params) {

        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: window.BE.urls.taxlot_labels,
            params: _.assignIn({
                selected_taxlots: selected_taxlots,
                select_all_checkbox: select_all_checkbox,
                organization_id: user_service.get_organization().id
            }, search_params),
            data: {
                add_label_ids: add_label_ids,
                remove_label_ids: remove_label_ids
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;

    }


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
    function get_available_colors() {
        return [
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
    }

    /* "PRIVATE" METHODS */
    /* ~~~~~~~~~~~~~~~~~ */


    /*  Add a few properties to the label object so that it
        works well with UI components.
    */
    function update_label_w_local_props(lbl){
        // add bootstrap label class names
        lbl.label = label_helper_service.lookup_label(lbl.color);
        // create 'text' property needed for ngTagsInput control
        lbl.text = lbl.name;
        return lbl;
    }




    /* Public API */

    var label_factory = {

        //functions
        get_labels : get_labels,
        get_labels_for_org : get_labels_for_org,
        create_label : create_label,
        create_label_for_org : create_label_for_org,
        update_label : update_label,
        update_label_for_org : update_label_for_org,
        delete_label : delete_label,
        delete_label_for_org : delete_label_for_org,
        update_property_labels : update_property_labels,
        update_taxlot_labels : update_taxlot_labels,
        get_available_colors : get_available_colors

    };

    return label_factory;

}]);
