/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// project services
angular.module('BE.seed.service.project', [])
.factory('project_service', [
  '$http',
  '$q',
  'user_service',
  'generated_urls',
  function ($http, $q, user_service, generated_urls) {
    
    var project_factory = { total_number_projects_for_user:0 };
    var urls = generated_urls;

    project_factory.get_projects = function() {

        var defer = $q.defer();
        $http({
            'method': 'GET',
            'url': urls.projects.get_projects,
            'params': {
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            project_factory.total_number_projects_for_user = (data.projects !== undefined ) ? data.projects.length : 0;
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };
    project_factory.get_project = function(project_slug) {

        var defer = $q.defer();
        $http({
            'method': 'GET',
            'url': urls.projects.get_project,
            'params': {
                'project_slug': project_slug,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.create_project = function(project) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'url': urls.projects.create_project,
            'data': {
                'project': project,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.update_project_name = function(project) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'url': urls.projects.update_project,
            'data': {
                'project': project,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.add_buildings = function(project) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'url': urls.projects.add_buildings_to_project,
            'data': {
                'project': project,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.remove_buildings = function(project) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'url': urls.projects.remove_buildings_from_project,
            'data': {
                'project': project,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.add_buildings_status = function(project_loading_cache_key) {
        var defer = $q.defer();
        $http({
            'method': 'POST',
            'url': urls.projects.get_adding_buildings_to_project_status_percentage,
            'data': {'project_loading_cache_key': project_loading_cache_key}
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.delete_project = function(project_slug) {
        var defer = $q.defer();
        $http({
            'method': 'DELETE',
            'url': urls.projects.delete_project,
            'data': {
                'project_slug': project_slug,
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.get_datasets_count = function() {

        var defer = $q.defer();
        $http({
            'method': 'GET',
            'url': urls.seed.get_datasets_count,
            'params': {
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    project_factory.get_projects_count = function() {

        var defer = $q.defer();
        $http({
            'method': 'GET',
            'url': urls.projects.get_projects_count,
            'params': {
                'organization_id': user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };


    project_factory.move_buildings = function(source_project_slug, target_project_slug, buildings, select_all_checkbox, search_params, copy) {
        // moves or copies buildings from source_project to tartget_project

        var defer = $q.defer();
        $http({
            method: 'POST',
            'url': urls.projects.move_buildings,
            'data': {
                'source_project_slug': source_project_slug,
                'target_project_slug': target_project_slug,
                'buildings': buildings,
                'select_all_checkbox': select_all_checkbox,
                'search_params': search_params,
                'copy': copy
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    return project_factory;
}]);
