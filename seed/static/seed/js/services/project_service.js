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
            method: 'GET',
            url: '/api/v2/projects/',
            params: {
                organization_id: user_service.get_organization().id
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
            method: 'GET',
            url: '/api/v2/projects/get_project/',
            params: {
                project_slug: project_slug,
                organization_id: user_service.get_organization().id
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
            method: 'POST',
            url: '/api/v2/projects/',
            data: {
                name: project.name,
                compliance_type: project.compliance_type,
                description: project.description,
                end_date: project.end_date,
                deadline_date: project.deadline_date
            },
            params: {
                organization_id: user_service.get_organization().id
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
            method: 'PUT',
            url: '/api/v2/projects/update_project/',
            data: {
                name: project.name,
                is_compliance: project.is_compliance,
                end_date: project.end_date,
                deadline_date: project.deadline_date
            },
            params: {
                project_slug: project.slug,
                organization_id: user_service.get_organization().id
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
            method: 'PUT',
            url: '/api/v2/projects/add_buildings/',
            data: {
                project: project
            },
            params: {
                project_slug: project.slug,
                organization_id: user_service.get_organization().id
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
            method: 'PUT',
            url: '/api/v2/projects/remove_buildings/',
            data: {
                project: project.selected_buildings,
            },
            params: {
                project_slug: project.slug,
                organization_id: user_service.get_organization().id
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
            method: 'GET',
            url: '/api/v2/projects/add_building_status/',
            params: {project_loading_cache_key: project_loading_cache_key}
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
            method: 'DELETE',
            url: '/api/v2/projects/delete_project/',
            params: {
                project_slug: project_slug,
                organization_id: user_service.get_organization().id
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
            method: 'GET',
            url: '/api/v2/datasets/count/',
            params: {
                organization_id: user_service.get_organization().id
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
            method: 'GET',
            url: '/api/v2/projects-count/',
            params: {
                organization_id: user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };


    project_factory.move_buildings = function(source_project_slug, target_project_slug, buildings, select_all_checkbox, search_params, copy) {
        // moves or copies buildings from source_project to target_project

        var defer = $q.defer();
        $http({
            method: 'POST',
            url: '/api/v2/projects/move_buildings/',
            data: {
                source_project_slug: source_project_slug,
                target_project_slug: target_project_slug,
                buildings: buildings,
                select_all_checkbox: select_all_checkbox,
                search_params: search_params,
                copy: copy
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
