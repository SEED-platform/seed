/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// building services
angular.module('BE.seed.service.building', ['BE.seed.services.label_helper'])
  .factory('building_services', [
    '$http',
    'urls',
    'label_helper_service',
    'user_service',
    'generated_urls',
    'spinner_utility',
    function ($http, urls, label_helper_service, user_service, generated_urls, spinner_utility) {

      var building_factory = {total_number_of_buildings_for_user: 0};

      building_factory.get_total_number_of_buildings_for_user = function () {
        // django uses request.user for user information
        return $http.get(window.BE.urls.get_total_number_of_buildings_for_user_url).then(function (response) {
          building_factory.total_number_of_buildings_for_user = response.data.buildings_count;
          return response.data;
        });
      };

      building_factory.get_building = function (building_id) {
        // django uses request.user for user information
        return $http.get(window.BE.urls.get_building_url, {
          params: {
            building_id: building_id,
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          _.forEach(response.data.projects, function (project) {
            var building = project.building;
            if (building.label) {
              building.label.label = label_helper_service.lookup_label(building.label.color);
            }
          });
          return response.data;
        });
      };

      /**
       *
       * @param query_string
       * @param number_per_page
       * @param page_number
       * @param order_by
       * @param sort_reverse
       * @param filter_params: If filter_params are provided, then project_slug will be ignored.
       * @param project_id
       * @param project_slug: Name of the project to constrain the query.
       * @returns {Promise}
       */
      building_factory.search_buildings = function (query_string, number_per_page, page_number, order_by, sort_reverse, filter_params, project_id, project_slug) {
        spinner_utility.show();
        return $http.post(urls.search_buildings, {
          q: query_string,
          number_per_page: number_per_page,
          page: page_number,
          order_by: order_by,
          sort_reverse: sort_reverse,
          filter_params: filter_params,
          project_id: project_id,
          project_slug: project_slug
        }).then(function (response) {
          spinner_utility.hide();
          return response.data;
        });
      };

      // building_factory.search_mapping_results = function (query_string, number_per_page, page_number, order_by, sort_reverse, filter_params, import_file_id, project_id, project_slug) {
      //   spinner_utility.show();
      //   return $http.post('/api/v2/import_files/' + import_file_id + '/filtered_mapping_results/', {}).then(function (response) {
      //     spinner_utility.hide();
      //     return response.data;
      //   });
      // };
      //
      // building_factory.search_matching_buildings = function (query_string, number_per_page, page_number, order_by, sort_reverse, filter_params, import_file_id) {
      //   spinner_utility.show({top: '75%'}, $('.section_content')[0]);
      //   return $http.post('/api/v2/import_files/' + import_file_id + '/filtered_mapping_results/', {}).then(function (response) {
      //     spinner_utility.hide();
      //     return response.data;
      //   });
      // };

      building_factory.save_match = function (source_building_id, target_building_id, create_match) {
        return $http.post(urls.save_match, {
          source_building_id: source_building_id,
          target_building_id: target_building_id,
          create_match: create_match,
          organization_id: user_service.get_organization().id
        }).then(function (response) {
          return response.data;
        });
      };

      building_factory.update_building = function (building, organization_id) {
        return $http.put(urls.update_building, {
          building: building,
          organization_id: organization_id
        }).then(function (response) {
          return response.data;
        });
      };


      building_factory.get_columns = function (all_fields) {
        all_fields = all_fields || '';
        return $http.get(window.BE.urls.get_columns_url, {
          params: {
            all_fields: all_fields,
            organization_id: user_service.get_organization().id
          }
        }).then(function (response) {
          return response.data;
        });
      };

      building_factory.get_matching_results = function (import_file_id) {
        return $http.get("/api/v2/import_files/" + import_file_id + "/matching_results/", {
          params: {}
        }).then(function (response) {
          return response.data;
        });
      };

      building_factory.delete_duplicates_from_import_file = function (import_file_id) {
        $http.get(window.BE.urls.delete_duplicates_from_import_file_url, {
          params: {
            import_file_id: import_file_id
          }
        }).then(function (response) {
          return response.data;
        });
      };

      /**
       * start the delete buildings process
       */
      building_factory.delete_buildings = function (search_payload) {
        spinner_utility.show();
        return $http.delete(generated_urls.seed.delete_buildings, {
          data: {
            organization_id: user_service.get_organization().id,
            search_payload: search_payload
          }
        }).then(function (response) {
          spinner_utility.hide();
          return response.data;
        });
      };

      building_factory.get_confidence_ranges = function () {
        // low, med, and high could be generate server side
        var LOW, MED, HIGH;
        LOW = 0.4;
        MED = 0.75;
        HIGH = 1.0;
        return {
          low: LOW,
          medium: MED,
          high: HIGH
        };
      };

      building_factory.confidence_text = function (confidence) {
        // this could be moved into a directive
        var conf_range = this.get_confidence_ranges();

        if (confidence < conf_range.low) {
          return 'low';
        } else if (confidence >= conf_range.low && confidence < conf_range.medium) {
          return 'med';
        } else if (confidence >= conf_range.medium <= conf_range.high) {
          return 'high';
        }
        else {
          return '';
        }
      };


      return building_factory;
    }]);
