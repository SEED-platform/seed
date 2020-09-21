/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

/** Post_office Service:
 --------------------------------------------------
 Provides methods to access email templates and to send emails on the server 
*/
angular.module('BE.seed.service.postoffice', []).factory('postoffice_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var template_factory = {};

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

    // Extracting EmailTemplate objects by running a get request on postoffice 
    template_factory.get_templates = function () {
      return $http.get('/api/v3/postoffice/', {
        params: {
          organization_id: user_service.get_organization().id,
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

	// Create new template
    template_factory.new_template = function (data) {
      return $http.post('/api/v3/postoffice/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    // Renaming the selected template in the available templates drop-down menu (Organization-->Email Templates)
    template_factory.update_template = function (id, data) {
      if (id === null) {
        Notification.error('This group is protected from modifications');
        return $q.reject();
      }
      return $http.put('/api/v3/postoffice/' + id + '/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      }).then(function (response) {
        return response.data.data;
      });
    };

    // Removing the selected template in the available templates drop-down menu (Organization-->Email Templates)
    template_factory.remove_template = function (id) {
      if (id === null) {
        Notification.error('This template is protected from modifications');
        return $q.reject();
      }
      return $http.delete('/api/v3/postoffice/' + id + '/', {
        params: {
          organization_id: user_service.get_organization().id
        }
      });
    };

    // Passing data from the Front End to the View
    template_factory.send_templated_email = function (template_name, inventory_id, inventory_type) {
      return $http.post('/api/v3/postoffice_email/', {
        // The from email_field has to be passed to the view, can put a dummy email in place. 
        from_email: "dummy_email@example.com",
        name: template_name,
        inventory_id: inventory_id,
        inventory_type: inventory_type
      }, {
        params: {
          organization_id: user_service.get_organization().id,
        }
      }).then(function (response) {
        return response.data;
      }).catch(_.constant('Error fetching templates'));
    };

    return template_factory;
  }]);


