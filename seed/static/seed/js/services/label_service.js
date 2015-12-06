angular.module('BE.seed.service.label', 
    []).factory('label_service', [ '$http',
                                    '$q',
                                    '$timeout',
                                    '$log',
                                    'user_service',
                                    'label_helper_service',
                                    'urls',
                        function (  $http, 
                                    $q, 
                                    $timeout,
                                    $log,
                                    user_service,
                                    label_helper_service,
                                    urls
                                    ) {


    /** Label Service:  
        --------------------------------------------------
        Provides methods to CRUD labels on the server
        as well as apply and remove labels to buildings.
    */




    /** Returns an array of labels.
    
        @param {object} search  -   Optional search object. If provided, server should
                                    mark each label in the response with a boolean 
                                    property 'exists-in-set'

        @return {object}            Returns a promise object that will resolve an
                                    array of label objects on success.

        Label objects have the following properties, with 'text' and 'color' props assigned locally.
        
            id {integer}            the id of the label
            name {string}           the text that appears in the label
            text {string}           same as name, needed for ngTagsInput control
            color {string}          the text description of the label's color (e.g. 'blue')
            label {string}          the css class (usually in bootstrap) used to generate the color style
                                    (poorly named, we should refactor to 'css-class' or something more accurate
                                    or change how color is applied)
            num_buildings_updated {boolean}     if a search object was passed in, this boolean indicates
                                                how many buildings in the current filtered set have this label

        For example
            {                
                id: 8                
                name: "test9"
                color: "blue"
                label: "primary"
                num_buildings_updated : 12
            }
    */
    
    function get_labels(selected_buildings, select_all_checkbox, search_params) {
        var defer = $q.defer();
       
        var searchArgs = _.extend({
            'selected_buildings' : selected_buildings,
            'select_all_checkbox' : select_all_checkbox,
             organization_id: user_service.get_organization().id
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

        @return {object}    Returns a promise object which will resolve
                            with either a success if the label was created
                            on the server, or an error if the label could not be
                            created on the server. 

                            Return object should also have a 'label' property assigned 
                            to the newly created label object.
    */
    function create_label(label){
        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': window.BE.urls.label_list,
            'data': label
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
        
        @param {object} label object, which must include label ID. 

        @return {object}    Returns a promise object which will resolve
                            with either a success if the label was updated, 
                            or an error if not.                             
                            Return object should also have a 'label' property assigned 
                            to the updated label object.
    */
    function update_label(label){
        var defer = $q.defer();
        $http({
            method: 'PUT',
            'url': window.BE.urls.label_list + label.id + '/',
            'data': label,
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

    /*  Delete a label from the set of labels for an organization 

        @param {object} label object, which must include label ID. 

        @return {object}    Returns a promise object which will resolve
                            with either a success if the label was deleted, 
                            or an error if not
    */
    function delete_label(label){
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            'url': window.BE.urls.label_list + label.id + '/',
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /* FUNCTIONS FOR LABELS WITHIN BUIDINGS  */
    /* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/

    /*  

    This method updates selected buildings with a group of "add" labels
    and a group of "remove" labels. 

    
    @param {array} add_label_ids            An array of label ids to apply to selected buildings
    @param {array} remove_label_ids         An array of label ids to remove from selected buildings
    @param {object} search                  A reference to the Search object, which includes
                                            properties for selected buildings, active filters
                                            and the status of the 'select all' checkbox.

    @return {object}                        A promise object that resolves server response
                                            (success or error)

    */
    function update_building_labels(add_label_ids, remove_label_ids, selected_buildings, select_all_checkbox, search_params) {
        var defer = $q.defer();
        $http({
            method: 'PUT',
            'url': window.BE.urls.update_building_labels,
            'params': _.extend({
                'selected_buildings' : selected_buildings,
                'select_all_checkbox': select_all_checkbox
            }, search_params),
            'data': {
                'add_label_ids': add_label_ids,
                'remove_label_ids': remove_label_ids
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

        @return {array}     List of label option objects 

        Label option objects have the following structure
        {
            'label' : {string} name of bootstrap class for label
            'color' : {string} text description of color
        }

        NOTE: At some point label colors should be defined on the server and not 
        directly related to bootstrap colors. If we do stay with Bootstrap colors
        we should change the property names to  something like 'bootstrap-class' and 
        'color-description' to make them more clear.

    */
    function get_available_colors() {
        return [
            {
                'label': 'success',
                'color': 'green'
            },
            {
                'label': 'danger',
                'color': 'red'
            },
            {
                'label': 'default',
                'color': 'gray'
            },
            {
                'label': 'warning',
                'color': 'orange'
            },
            {
                'label': 'info',
                'color': 'light blue'
            },
            {
                'label': 'primary',
                'color': 'blue'
            }
        ];
    }

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
        get_labels : get_labels ,
        create_label : create_label,
        update_label : update_label,
        delete_label : delete_label,
        update_building_labels : update_building_labels,
        get_available_colors : get_available_colors
    
    };

    return label_factory;

}]);
