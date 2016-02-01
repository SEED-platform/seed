/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// building services
angular.module('BE.seed.service.building', ['BE.seed.services.label_helper'])
.factory('building_services', [
  '$http',
  '$q',
  'urls',
  'label_helper_service',
  'user_service',
  'generated_urls',
  function ($http, $q, urls, label_helper_service, user_service, generated_urls) {

    var building_factory = { total_number_of_buildings_for_user: 0};

    building_factory.get_total_number_of_buildings_for_user = function() {
        // django uses request.user for user information
        var defer = $q.defer();
        $http({
            method: 'GET',
            'url': window.BE.urls.get_total_number_of_buildings_for_user_url
        }).success(function(data, status, headers, config) {
            building_factory.total_number_of_buildings_for_user = data.buildings_count;
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    building_factory.get_building = function(building_id) {
        // django uses request.user for user information
        var defer = $q.defer();
        $http({
            method: 'GET',
            'url': window.BE.urls.get_building_url,
            'params': {
                'building_id': building_id,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            for (var i = 0; i < data.projects.length; i++) {
                var building = data.projects[i].building;
                if (typeof building.label !== "undefined") {
                    building.label.label = label_helper_service.lookup_label(building.label.color);
                }
            }
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    building_factory.search_buildings = function(query_string, number_per_page, page_number, order_by, sort_reverse, filter_params, project_id, project_slug) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'data': {
                'q': query_string,
                'number_per_page': number_per_page,
                'page': page_number,
                'order_by': order_by,
                'sort_reverse': sort_reverse,
                'filter_params': filter_params,
                'project_id': project_id,
                'project_slug': project_slug
            },
            'url': urls.search_buildings
        }).success(function(data, status, headers, config){
            defer.resolve(data);
        }).error(function(data, status, headers, config){
            defer.reject(data, status);
        });
        return defer.promise;
    };

    building_factory.search_building_snapshots = function(query_string, number_per_page, page_number, order_by, sort_reverse, filter_params, import_file_id, project_id, project_slug) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'data': {
                'q': query_string,
                'number_per_page': number_per_page,
                'page': page_number,
                'order_by': order_by,
                'sort_reverse': sort_reverse,
                'filter_params': filter_params,
                'project_id': project_id,
                'import_file_id': import_file_id,
                'project_slug': project_slug
            },
            'url': urls.search_building_snapshots
        }).success(function(data, status, headers, config){
            defer.resolve(data);
        }).error(function(data, status, headers, config){
            defer.reject(data, status);
        });
        return defer.promise;
    };

    building_factory.search_matching_buildings = function(query_string, number_per_page, page_number, order_by, sort_reverse, filter_params, import_file_id) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'data': {
                'q': query_string,
                'number_per_page': number_per_page,
                'page': page_number,
                'order_by': order_by,
                'sort_reverse': sort_reverse,
                'filter_params': filter_params,
                'import_file_id': import_file_id
            },
            'url': urls.search_building_snapshots
        }).success(function(data, status, headers, config){
            defer.resolve(data);
        }).error(function(data, status, headers, config){
            defer.reject(data, status);
        });
        return defer.promise;
    };

    building_factory.save_match = function(source_building_id, target_building_id, create_match) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'data': {
                'source_building_id': source_building_id,
                'target_building_id': target_building_id,
                'create_match': create_match,
                'organization_id': user_service.get_organization().id
            },
            'url': urls.save_match
        }).success(function(data, status, headers, config){
            defer.resolve(data);
        }).error(function(data, status, headers, config){
            defer.reject(data, status);
        });
        return defer.promise;
    };

    building_factory.update_building = function(building, organization_id) {
        var defer = $q.defer();
        $http({
            'method': 'PUT',
            'data': {
                'building': building,
                'organization_id': organization_id
            },
            'url': urls.update_building
        }).success(function(data, status, headers, config){
            defer.resolve(data);
        }).error(function(data, status, headers, config){
            defer.reject(data, status);
        });
        return defer.promise;
    };



    building_factory.get_columns = function(is_project, project_slug, all_fields) {
        var defer = $q.defer();
        all_fields = all_fields || "";
        $http({
            method: 'GET',
            'url': window.BE.urls.get_columns_url,
            'params': {
                'is_project': is_project,
                'project_slug': project_slug,
                'all_fields': all_fields,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /*
     * create_column_array: returns an array of columns used to set table
     *   headers from an array of all possible columns and an array of 
     *   keys 
     * 
     * @param {Array} all_columns an array of Objects with a default key of
     *   `sort_column` to filter
     * @param {Array} column_names an array of String names to filter the 
     *   `all_columns` array 
     * @param {String} key (optional) if provided will filter on `key`,
     *   otherwise filters on `sort_column`
     */
    building_factory.create_column_array = function(all_columns, column_names, key) {
        key = key || "sort_column";
        return all_columns.filter(function(f) {
            return column_names.indexOf(f[key]) > -1;
        });
    };

    building_factory.get_PM_filter_by_counts = function(import_file_id) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            'url': window.BE.urls.get_PM_filter_by_counts_url,
            'params': {
                'import_file_id': import_file_id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };
    
    building_factory.delete_duplicates_from_import_file = function(import_file_id) {
        var defer = $q.defer();
        $http({
            method: 'GET',
            'url': window.BE.urls.delete_duplicates_from_import_file_url,
            'params': {
                'import_file_id': import_file_id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    /**
     * start the delete buildings process
     */
    building_factory.delete_buildings = function(search_payload) {
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            'url': generated_urls.seed.delete_buildings,
            'data': {
                'organization_id': user_service.get_organization().id,
                'search_payload': search_payload
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    building_factory.get_confidence_ranges = function() {
        // low, med, and high could be generate server side
        var LOW, MED, HIGH;
        LOW = 0.4;
        MED = 0.75;
        HIGH = 1.0;
        return {
            'low': LOW,
            'medium': MED,
            'high': HIGH
        };
    };

    building_factory.confidence_text = function(confidence) {
        // this could be moved into a directive
        var conf_range = this.get_confidence_ranges();

        if (confidence < conf_range.low) {
            return "low";
        } else if (confidence >= conf_range.low && confidence < conf_range.medium) {
            return "med";
        } else if (confidence >= conf_range.medium <= conf_range.high) {
            return "high";
        }
        else {
            return "";
        }
    };


    return building_factory;
}]);
