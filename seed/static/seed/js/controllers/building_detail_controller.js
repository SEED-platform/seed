/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.building_detail', [])
.controller('building_detail_controller', [
  '$scope',
  '$routeParams',
  '$uibModal',
  '$log',
  'building_services',
  'project_service',
  'building_payload',

  // include ts data payload
  'building_finer_energy_payload',
  'building_monthly_payload',
  // include ts data payload ends

  // include previous gb request info
  'gb_req_info',
  // include previous gb request info ends

  'all_columns',
  'audit_payload',
  'urls',
  '$filter',
  '$location',
  'audit_service',
  'label_helper_service',
  'default_columns',
  function($scope, $routeParams, $uibModal, $log, building_services, project_service, building_payload,
           building_finer_energy_payload, building_monthly_payload, gb_req_info, all_columns,
           audit_payload, urls, $filter, $location, audit_service, label_helper_service, default_columns) {
    $scope.user = {};
    $scope.user.building_id = $routeParams.building_id;
    $scope.user.project_slug = $routeParams.project_id;
    $scope.projects = [];
    $scope.labels = _.map(building_payload.labels, function(lbl) {
      lbl.label = label_helper_service.lookup_label(lbl.color);
      return lbl;
    });
    $scope.building = building_payload.building;
    $scope.user_role = building_payload.user_role;
    $scope.user_org_id = building_payload.user_org_id;
      // TODO: Fix this -- filter is not defined
    //$scope.building.recent_sale_date = $filter('date')($scope.building.recent_sale_date, 'MM/dd/yyyy');
    $scope.imported_buildings = building_payload.imported_buildings;
    $scope.projects = building_payload.projects;
    $scope.fields = all_columns.fields;
    $scope.default_columns = default_columns.columns;
    $scope.building_copy = {};
    $scope.data_columns = [];
    $scope.audit_logs = audit_payload.audit_logs;
    $scope.green_button_filenames = [];

    // scope models for GreenButton Request Information
    $scope.time_type = '';
    $scope.active = '';
    $scope.loopback = '';

    $scope.gb_req_flag = 'N';
    $scope.gb_req_url = '';
    $scope.gb_req_min_date_para = '';
    $scope.gb_req_max_date_para = '';
    $scope.gb_req_date_pattern = '';
    // scope models ends

    // add ts data object to $scope
    if(building_finer_energy_payload['status'] === 'success'){
        $scope.finer_ts_data_meta = [];
        $scope.finer_ts_data_readings = [];
        $scope.finer_ts_data_interval = '0';

        if(building_finer_energy_payload['reading'].length>0){
            $scope.finer_ts_data_readings = building_finer_energy_payload['reading'];

            $scope.finer_ts_data_meta = [];
            $scope.finer_ts_data_meta.push({'key':'Energy Type', 'value':building_finer_energy_payload['tags']['energy_type'][0]});
            $scope.finer_ts_data_meta.push({'key':'Tens Multiplier', 'value':building_finer_energy_payload['tags']['tens'][0]});
            $scope.finer_ts_data_meta.push({'key':'Unit', 'value':building_finer_energy_payload['tags']['uom'][0]});

            $scope.finer_ts_data_interval = building_finer_energy_payload['tags']['interval'][0];
        }

        $scope.finer_ts_data_flag = true;
    }else {
        $scope.finer_ts_data_flag = true;
        $scope.finer_ts_data_readings = [];
        $scope.finer_ts_data_meta = [];
        $scope.finer_ts_data_error = building_finer_ts_data_payload['status'];
    }

    if(building_monthly_payload['status'] === 'success'){
        $scope.monthly_data_readings = [];

        if(building_monthly_payload['reading'].length>0){
            $scope.monthly_data_readings = building_monthly_payload['reading'];
        }

        $scope.monthly_data_flag = true;
    }else {
        $scope.monthly_data_flag = true;
        $scope.monthly_data_readings = [];
        $scope.monthly_data_error = building_monthly_payload['status'];
    }
    // add ts data object to $scope ends

    // parse gb_req_info
    if(gb_req_info['status'] === 'found'){
        $scope.gb_req_flag = 'Y';
        $scope.gb_req_url = gb_req_info['url'];
        $scope.gb_req_subscription_id = gb_req_info['subscription_id'];
        $scope.gb_req_min_date_para = gb_req_info['min_date_para'];
        $scope.gb_req_max_date_para = gb_req_info['max_date_para'];
        $scope.time_type = gb_req_info['time_type'];
        $scope.gb_req_date_pattern = gb_req_info['date_pattern'];
        $scope.active = gb_req_info['active'];
    }
    // parse gb_req_info ends

    // gather green button filenames
    building_payload.imported_buildings.forEach(function(e) {
        if (e.source_type === 6) { // GREEN_BUTTON_BS
            $scope.green_button_filenames.push(e.import_file_name);
        }
    });

    // set the tab
    $scope.section = $location.hash();

    $scope.status = {
        isopen: false
    };

    $scope.time_type_change = function(time_type){
        $scope.time_type = time_type;
    }

    $scope.active_change = function(active){
        $scope.active = active;
    }

    $scope.loopback_change = function(loopback){
        $scope.loopback = loopback;
    }

    $scope.save_gb_request_info = function(){
        //TODO Front-end validation and URL request testing

        // read user front-end input
        var gb_url_input = angular.element(document.querySelector('#gb_url'))[0].value;
        var gb_subscription_id = angular.element(document.querySelector('#gb_subscription_id'))[0].value;
        var min_time_para = angular.element(document.querySelector('#min_para'))[0].value;
        var max_time_para = angular.element(document.querySelector('#max_para'))[0].value;
        var time_type = $scope.time_type;
        var date_pattern = angular.element(document.querySelector('#date_pattern'))[0].value;
        var active_flag = $scope.active;
        var loopback_flag = $scope.loopback;
        // read user front-end input ends

        // empty input check
        if(!(gb_url_input && min_time_para && max_time_para && time_type && active_flag && gb_subscription_id
                && ($scope.gb_req_flag==='Y' || loopback_flag)
                && (time_type==='timestamp' || date_pattern))){
            alert('Please fill all the fields!');
            return;
        }
        // empty check ends

        // get canonical building ID from $scope
        var canonical_building_id = $scope.building.canonical_building;
        var building_snapshot_id = $scope.building.id;
        // get building ID ends

        // assemble save-to-DB data
        var data = {};
        data['url'] = gb_url_input;
        data['subscription_id'] = gb_subscription_id;
        data['min_date_parameter'] = min_time_para;
        data['max_date_parameter'] = max_time_para;
        data['building_id'] = canonical_building_id;
        data['time_type'] = time_type;
        if(time_type === 'date'){
            data['date_pattern'] = date_pattern;
        }else {
            data['date_pattern'] = '';
        }
        data['active'] = active_flag;
        data['loopback'] = loopback_flag;
        // assemble save-to-DB data ends

        // call building_services save_gb_request_info method
        $scope.$emit('show_saving');
        building_services.save_gb_request_info(data)
            .then(function (data){
                // resolve promise
                audit_service.get_building_logs($scope.building.canonical_building)
                    .then(function(data){
                        $scope.audit_logs = data.audit_logs;
                    });
                $scope.$emit('finished_saving');
                alert('Saving finished');
            }, function (data, status){
                // reject promise
                $scope.$emit('finished_saving');
            }).catch(function (data) {
                console.log( String(data) );
            });
        // call method ends
    }

    var get_labels = function(building) {
        return _.map(building.labels, function(lbl) {
          lbl.label = label_helper_service.lookup_label(lbl.color);
          return lbl;
        });
    };

    $scope.labels = get_labels(building_payload);

    /**
     * is_project: returns true is building breadcrumb is from a project, used
     *   to hide/show the project breadcrumb url, i.e. return to all buildings
     *   or a project.
     */
    $scope.is_project = function() {
        if (typeof $scope.user.project_slug === "undefined") {
            return false;
        } else {
            return true;
        }
    };

    /**
     * is_active_project: returns true if `project` is the project breadcrumb.
     *   Used to highlight the table row for the active project in a list of
     *   compliance projects
     */
    $scope.is_active_project = function(project) {
        var p = $scope.project || {};
        return p.id === project.id;
    };


    /**
     * has_projects: used to show a custom table in the case no projects exist
     *   for a user's org.
     */
    $scope.user.has_projects = function() {
        // return true if user has any projects
        try {
            return $scope.projects.length > 0;
        } catch(err) {
            console.log(err);
            return false;
        }
    };


    /**
     * set_building_attribute: sets the building attribute from a star click
     */
    $scope.set_building_attribute = function (parent, field_name, extra_data) {
        var f = field_name.key || field_name;
        if (typeof extra_data !== "undefined" && extra_data){
            $scope.building.extra_data[f] = parent.extra_data[f];
            $scope.building.extra_data_sources[f] = parent.id;
        } else {
            $scope.building[f] = parent[f];
            $scope.building[f + '_source'] = parent.id;
        }
        // turn of master source star if set on another file
        if (!parent.is_master) {
            angular.forEach($scope.imported_buildings, function (b) {
                b.is_master = false;
            });
        }
    };

    /**
     * save_building_state: saves the building state in case cancel gets clicked
     */
    $scope.save_building_state = function () {
        $scope.building_copy = angular.copy($scope.building);
    };

    /**
     * restore_building: restores the building from its copy
     *   and hides the edit fields
     */
    $scope.restore_building = function () {
        $scope.building = $scope.building_copy;
        $scope.building.edit_form_showing = false;
    };

    /**
     * is_valid_key: checks to see if the key or attribute should be excluded
     *   from being copied from parent to master building
     */
    $scope.is_valid_key = function (key) {
        var known_invalid_keys = [
            'best_guess_confidence',
            'best_guess_canonical_building',
            'canonical_building',
            'canonical_for_ds',
            'children',
            'confidence',
            'created',
            'extra_data',
            'extra_data_sources',
            'id',
            'is_master',
            'import_file',
            'import_file_name',
            'last_modified_by',
            'match_type',
            'modified',
            'model',
            'parents',
            'pk',
            'super_organization',
            'source_type',
            'duplicate',
            'co_parent'
        ];
        var no_invalid_key = known_invalid_keys.indexOf(key) === -1;

        return (key.indexOf('_source') === -1 &&
                key.indexOf('extra_data') === -1 && key.indexOf('$$') === -1 &&
                no_invalid_key);
    };

    /**
     * make_source_default: makes one file the default source for all values it
     *   has unless the column does not have a value for a field
     */
    $scope.make_source_default = function (parent) {
        parent.is_master = true;
        // unselect any other master
        angular.forEach($scope.imported_buildings, function(b){
            if (b.id !== parent.id) {
                b.is_master = false;
            }
        });
        // main attributes
        angular.forEach(parent, function (val, key){
            if (val !== null && $scope.is_valid_key(key)){
                $scope.building[key] = val;
                $scope.building[key + '_source'] = parent.id;
            }
        });
        // extra_data
        angular.forEach(parent.extra_data, function (val, key){
            if (val !== null){
                $scope.building.extra_data[key] = val;
                $scope.building.extra_data_sources[key] = parent.id;
            }
        });
    };

    /**
     * save_building: saves the building's updates
     */
    $scope.save_building = function (){
        $scope.$emit('show_saving');
        building_services.update_building($scope.building, $scope.user_org_id)
        .then(function (data){
            // resolve promise
            audit_service.get_building_logs($scope.building.canonical_building)
            .then(function(data){
                $scope.audit_logs = data.audit_logs;
            });
            $scope.$emit('finished_saving');
        }, function (data, status){
            // reject promise
            $scope.$emit('finished_saving');
        }).catch(function (data) {
            console.log( String(data) );
        });
    };

    /**
     * set_self_as_source: saves the building's updates. If the optional
     *    ``extra_data`` param is passed and is true, the ``field_name``
     *    attribute will be applied to the building's extra_data attribute and
     *    the building object itself.
     *
     *   ex. $scope.building = {
               gross_floor_area: 12000,
               gross_floor_area_source: 33,
               extra_data: {
                  special_id: 1
               },
               extra_data_sources: {
                  special_id: 33
               },
               id: 10,
               pk: 10
             };

             $scope.set_self_as_source('gross_floor_area', false);
             // $scope.building.gross_floor_area_source is 10

             $scope.set_self_as_source('special_id', true);
             // $scope.building.extra_data.special_id is 10

     *
     * @param {string} field_name: the name of the building attribute
     * @param {bool} extra_data (optional): if true, set the source of the
     *    extra_data attribute
     */
    $scope.set_self_as_source = function (field_name, extra_data){
        if (extra_data) {
            $scope.building.extra_data_sources[field_name] = $scope.building.id;
        } else {
            $scope.building[field_name + '_source'] = $scope.building.id;
        }
        angular.forEach($scope.imported_buildings, function (b) {
            b.is_master = false;
        });
    };


    /**
     * generate_data_columns: sets $scope.data_columns to be a list
     * of all the data (fixed column and extra_data) fields for
     * $scope.building and each $scope.imported_buildings, which
     * are concatenated in init() and passed in as param ``buildings``.
     * Keys/fields are not duplicated. Only add columns that are in the
     * default_columns, if default_columns is not empty.
     *
     * @param {Array} buildings: concatenated list of buildings
     */
    $scope.generate_data_columns = function(buildings) {
        var data_columns = [];
        var key_list = [];
        var check_defaults = !!$scope.default_columns.length;

        // handle extra_data
        angular.forEach(buildings, function(b){
            angular.forEach(b.extra_data, function (val, key){
                // Duplicate check and check if default_columns is used and if field in columns
                if (key_list.indexOf(key) === -1 && (!check_defaults || (check_defaults && $scope.default_columns.indexOf(key) > -1))) {
                    key_list.push(key);
                    data_columns.push({
                        "key": key,
                        "type": "extra_data"
                    });
                }
            });
        });

        // handle building properties
        angular.forEach($scope.building, function ( val, key ) {
            // Duplicate check and check if default_columns is used and if field in columns
            if ( $scope.is_valid_key(key) && typeof val !== "undefined" && key_list.indexOf(key) === -1 &&
                (!check_defaults || (check_defaults && $scope.default_columns.indexOf(key) > -1))) {
                key_list.push(key);
                data_columns.push({
                    "key": key,
                    "type": "fixed_column"
                });
            }
        });

        if (check_defaults) {
            data_columns.sort(function(a,b) {
                if ($scope.default_columns.indexOf(a.key) < $scope.default_columns.indexOf(b.key)) {
                    return -1;
                } else {
                    return 1;
                }
            });
        }

        $scope.data_columns = data_columns;
    };

    /**
     * create_note
     */
    $scope.open_create_note_modal = function(existing_note) {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/create_note_modal.html',
            controller: 'create_note_modal_ctrl',
            resolve: {
                building: function () {
                    return $scope.building;
                },
                note: function() {
                    return existing_note;
                }
            }
        });

        modalInstance.result.then(
            function (note) {
                if (typeof existing_note !== 'undefined') {
                    angular.extend(existing_note, note);
                } else {
                    $scope.audit_logs.unshift(note);
                }
        }, function (message) {
                $log.info(message);
        });
    };

    /**
     * sets the ``$scope.section`` var to show the proper tab/section of the
     * page.
     * @param {string} section
     */
    $scope.set_location = function (section) {
        $scope.section = section;
    };

    /**
     * returns a number
     */
    $scope.get_number = function ( num ) {
        if ( !angular.isNumber(num) && num !== null && typeof num !== "undefined") {

            return +num.replace(/,/g, '');
        }
        return num;
    };

    $scope.open_update_building_labels_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/building_detail_update_labels_modal.html',
            controller: 'building_detail_update_labels_modal_ctrl',
            resolve: {
                building: function () {
                    return $scope.building;
                }
            }
        });
        modalInstance.result.then(
            function () {
                // Grab fresh building data for get_labels()
                var canonical_id = $scope.building.canonical_building;
                building_services.get_building(canonical_id).then(function(building_refresh) {
                    $scope.labels = get_labels(building_refresh);
                });
            },
            function (message) {
               //dialog was 'dismissed,' which means it was cancelled...so nothing to do.
            }
        );
    };

    /**
     * init: sets default state of building detail page, gets the breadcrumb
     *   project if exists, sets the field arrays for each section, performs
     *   some date string manipulation for better display rendering,
     *   and gets all the extra_data fields
     *
     */
    var init = function() {
        $scope.building_detail_fields = $scope.fields.filter(function (f) {
            return f.field_type === 'building_information';
        });
        $scope.contact_fields = $scope.fields.filter(function (f) {
            return f.field_type === 'contact_information';
        });
        // find all the floor area fields for the building
        $scope.floor_area_fields = [];
        angular.forEach($scope.building, function(value, key) {
            if (~angular.lowercase(key).indexOf('area') && !~angular.lowercase(key).indexOf('_source')) {
                $scope.floor_area_fields.push({
                    title: key,
                    sort_column: key
                });
            }
        });
        angular.forEach($scope.building.extra_data, function(value, key) {
            if (~angular.lowercase(key).indexOf('area')) {
                $scope.floor_area_fields.push({
                    title: key,
                    sort_column: key,
                    extra_data: true
                });
            }
        });

        $scope.building = building_payload.building;
        $scope.building.recent_sale_date = $filter('date')($scope.building.recent_sale_date, 'MM/dd/yyyy');
        $scope.building.year_ending = $filter('date')($scope.building.year_ending, 'MM/dd/yyyy');
        $scope.building.release_date = $filter('date')($scope.building.release_date, 'MM/dd/yyyy');
        $scope.building.generation_date = $filter('date')($scope.building.generation_date, 'MM/dd/yyyy');
        $scope.building.modified = $filter('date')($scope.building.modified, 'MM/dd/yyyy');
        $scope.building.created = $filter('date')($scope.building.created, 'MM/dd/yyyy');
        $scope.projects = building_payload.projects;
        if ($scope.is_project()){
            project_service.get_project($scope.user.project_slug).then(function(data) {
                    // resolve promise
                    $scope.project = data.project;
                }, function(data, status) {
                    // reject promise
                    console.log({data: data, status: status});
                }
            );
        }
        $scope.generate_data_columns(
            [$scope.building].concat($scope.imported_buildings)
        );
    };
    // fired on controller loaded
    init();
}]);
