/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// project services
angular.module('BE.seed.service.project', [])
  .factory('project_service', [
    '$http',
    'user_service',
    function ($http, user_service) {

      var project_factory = {total_number_projects_for_user: 0};

      // project_factory.get_projects = function () {
      //   return $http.get('/api/v2/projects/', {
      //     params: {
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     project_factory.total_number_projects_for_user = _.has(response.data.projects, 'length') ? response.data.projects.length : 0;
      //     return response.data;
      //   });
      // };

      // project_factory.get_project = function (project_slug) {
      //   return $http.get('/api/v2/projects/get_project/', {
      //     params: {
      //       project_slug: project_slug,
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      // project_factory.create_project = function (project) {
      //   return $http.post('/api/v2/projects/', {
      //     name: project.name,
      //     compliance_type: project.compliance_type,
      //     description: project.description,
      //     end_date: project.end_date,
      //     deadline_date: project.deadline_date
      //   }, {
      //     params: {
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      // project_factory.update_project_name = function (project) {
      //   return $http.put('/api/v2/projects/update_project/', {
      //     name: project.name,
      //     is_compliance: project.is_compliance,
      //     end_date: project.end_date,
      //     deadline_date: project.deadline_date
      //   }, {
      //     params: {
      //       project_slug: project.slug,
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      // project_factory.add_buildings = function (project) {
      //   return $http.put('/api/v2/projects/add_buildings/', {
      //     project: project
      //   }, {
      //     params: {
      //       project_slug: project.slug,
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      // project_factory.remove_buildings = function (project) {
      //   return $http.put('/api/v2/projects/remove_buildings/', {
      //     project: project.selected_buildings
      //   }, {
      //     params: {
      //       project_slug: project.slug,
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      // project_factory.add_buildings_status = function (project_loading_cache_key) {
      //   return $http.get('/api/v2/projects/add_building_status/', {
      //     params: {
      //       project_loading_cache_key: project_loading_cache_key
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      // project_factory.delete_project = function (project_slug) {
      //   return $http.delete('/api/v2/projects/delete_project/', {
      //     params: {
      //       project_slug: project_slug,
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      project_factory.get_datasets_count = function () {
        return $http.get('/api/v2/datasets/count/', {
          params: {
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response.data;
        });
      };

      // project_factory.get_projects_count = function () {
      //   return $http.get('/api/v2/projects/count/', {
      //     params: {
      //       organization_id: user_service.get_organization().id
      //     }
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };


      // project_factory.move_buildings = function (source_project_slug, target_project_slug, buildings, select_all_checkbox, search_params, copy) {
      //   // moves or copies buildings from source_project to target_project
      //   return $http.post('/api/v2/projects/move_buildings/', {
      //     source_project_slug: source_project_slug,
      //     target_project_slug: target_project_slug,
      //     buildings: buildings,
      //     select_all_checkbox: select_all_checkbox,
      //     search_params: search_params,
      //     copy: copy
      //   }).then(function (response) {
      //     return response.data;
      //   });
      // };

      return project_factory;
    }]);
