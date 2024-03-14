/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 *
 * Provides methods to access email templates and to send emails on the server
 */
angular.module('BE.seed.service.postoffice', []).factory('postoffice_service', [
  '$http',
  '$q',
  'user_service',
  'naturalSort',
  ($http, $q, user_service, naturalSort) => {
    const template_factory = {};

    template_factory.sort_templates = (response) => response.data.data.sort((a, b) => naturalSort(a.name, b.name));

    /** Returns an array of templates.
     Returned EmailTemplate objects should have the following properties:
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
    * */
    template_factory.get_templates = () => template_factory.get_templates_for_org(user_service.get_organization().id);

    // Extracting EmailTemplate objects by running a get request on postoffice
    template_factory.get_templates_for_org = (organization_id) => $http
      .get('/api/v3/postoffice/', {
        params: {
          organization_id
        }
      })
      .then((response) => template_factory.sort_templates(response));

    // Create new template
    template_factory.new_template = (data, organization_id) => $http
      .post('/api/v3/postoffice/', data, {
        params: {
          organization_id
        }
      })
      .then((response) => response.data.data);

    // Renaming the selected template in the available templates drop-down menu (Organization-->Email Templates)
    template_factory.update_template = (id, data, organization_id) => {
      if (id === null) {
        Notification.error('This template is protected from modifications');
        return $q.reject();
      }
      return $http
        .put(`/api/v3/postoffice/${id}/`, data, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data.data);
    };

    // Removing the selected template in the available templates drop-down menu (Organization-->Email Templates)
    template_factory.remove_template = (id, organization_id) => {
      if (id === null) {
        Notification.error('This template is protected from modifications');
        return $q.reject();
      }
      return $http.delete(`/api/v3/postoffice/${id}/`, {
        params: {
          organization_id
        }
      });
    };

    template_factory.send_templated_email = (template_id, inventory_id, inventory_type) => template_factory.send_templated_email_for_org(template_id, inventory_id, inventory_type, user_service.get_organization().id);

    // Passing data from the Front End to the View
    template_factory.send_templated_email_for_org = (template_id, inventory_id, inventory_type, organization_id) => {
      const data = {
        from_email: 'dummy_email@example.com', // The from_email field has to be passed to the view, can put a dummy email in place.
        template_id,
        inventory_id,
        inventory_type
      };
      return $http
        .post('/api/v3/postoffice_email/', data, {
          params: {
            organization_id
          }
        })
        .then((response) => response.data)
        .catch(() => 'Error fetching templates');
    };

    template_factory.get_last_template = (organization_id) => (JSON.parse(localStorage.getItem('template')) || {})[organization_id];

    template_factory.save_last_template = (pk, organization_id) => {
      const template = JSON.parse(localStorage.getItem('template')) || {};
      template[organization_id] = _.toInteger(pk);
      localStorage.setItem('template', JSON.stringify(template));
    };

    return template_factory;
  }
]);
