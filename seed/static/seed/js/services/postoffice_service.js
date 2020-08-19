/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.postoffice', []).factory('postoffice_service', [
    '$http',
    'user_service',
    // 'cycle_id',
    // 'columns',
    // 'inventory_type',
    // 'profile_id',
    function ($http, user_service) {
      // , cycle_id, columns, inventory_type, profile_id
      var template_factory = {};
      /** Post_office Service:
       --------------------------------------------------
       Provides methods to add/edit templates on the server.
       */
  
  
      /** Returns an array of templates.
  
       Returned EmailTemplate objects should have the following properties,
  
       id {integer}            
       name {string}           
       description {string}
       subject {string}
       content {string}
       html_content {string}
       created {string}
       last_updated {string}
       default_template_id {integer}   
       language {string}
  
       */
  
      template_factory.get_templates = function () {
        return $http.get('/api/v3/postoffice/', {
          params: {
            organization_id: user_service.get_organization().id,
            // cycle_id: cycle_id,
            // inventory_type: inventory_type
          }
        }).then(function (response) {
          return response.data.data;
        });
      };
      // user_service.get_organization().id
  
      // template_factory.get_templates_for_org = function () {
      //   return $http.get('/api/v3/postoffice/', {
      //     // params: {
      //     //   organization_id: org_id
      //     // }
      //   }).then(function (response) {
      //     console.log("****************************************");
      //     console.log(response.data);
      //     console.log("****************************************");
      //     return response.data;
      //   });
      // };

      template_factory.send_templated_email = function (template_name, building_id) {
        console.log("SERVICE");
        console.log(template_name);
        console.log(building_id);
        return $http.post('/api/v3/postoffice_email/', {
            from_email: "hello@example.com",
            name: template_name,
            building_id: building_id
        },{
          params: {
            organization_id: user_service.get_organization().id,
            // cycle_id: cycle_id,
            // inventory_type: inventory_type
          }
        }).then(function (response) {
          return response.data;
        }).catch(_.constant('Error fetching templates'));
      };
      
      return template_factory;
    }]);
  
  
    