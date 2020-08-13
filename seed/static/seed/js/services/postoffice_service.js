/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.postoffice', []).factory('postoffice_service', [
    '$http',
    'user_service',
    function ($http, user_service) {
  
      var template_factory = {};
      /** Post_office Service:
       --------------------------------------------------
       Provides methods to add/edit templates on the server.
       */
  
  
      /** Returns an array of templates.
  
       Returned template objects should have the following properties,
       with 'text' and 'color' properties assigned locally.
  
       id {integer}            The id of the Cycle.
       name {string}           The text that appears in the Cycle.
       start_date {string}     Start date for Cycle.
       end_date {string}       End date for Cycle.
  
       */
  
      template_factory.get_templates = function () {
        return $http.get('/api/v3/postoffice/', {
          // params: {
          //   organization_id: org_id
          // }
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

    //   template_factory.send_templated_email = function (template_id) {
    //     return $http.post('/api/v3/postoffice_email/send_templated_email/', {
    //       params: {
    //         organization_id: org_id,
    //         id: template_id
    //       }
    //     }).then(function (response) {
    //       return response.data;
    //     });
    //   };
      
      return template_factory;
    }]);
  
  
    