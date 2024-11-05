/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.report_configurations', []).factory('report_configurations_service', [
  '$http',
  '$q',
  'user_service',
  'naturalSort',
  ($http, $q, user_service, naturalSort) => {
    const report_configurations_factory = {};

    report_configurations_factory.get_report_configurations = (organization_id = user_service.get_organization().id) => $http
      .get(`/api/v3/organizations/${organization_id}/report_configurations`, {})
      .then((response) => {
        const report_configurations = response.data.data.sort((a, b) => naturalSort(a.name, b.name));

        return report_configurations;
      });

    report_configurations_factory.get_last_report_configuration = () => {
      const organization_id = user_service.get_organization().id;
      return (JSON.parse(localStorage.getItem('report_configurations')) || {})[organization_id];
    };

    report_configurations_factory.save_last_report_configuration = (id) => {
      const organization_id = user_service.get_organization().id;
      const report_configurations = JSON.parse(localStorage.getItem('report_configurations')) || {};
      if (id === -1) {
        delete report_configurations[organization_id];
      } else {
        report_configurations[organization_id] = id;
      }
      localStorage.setItem('report_configurations', JSON.stringify(report_configurations));
    };

    report_configurations_factory.get_report_configuration = (id) => $http
      .get(`/api/v3/report_configurations/${id}/`, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data.data);

    report_configurations_factory.new_report_configuration = (data) => $http
      .post('/api/v3/report_configurations/', data, {
        params: {
          organization_id: user_service.get_organization().id
        }
      })
      .then((response) => response.data.data);

    report_configurations_factory.update_report_configuration = (id, data) => {
      if (id === null) {
        Notification.error('This report configuration is protected from modifications');
        return $q.reject();
      }
      return $http
        .put(`/api/v3/report_configurations/${id}/`, data, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data.data);
    };

    report_configurations_factory.remove_report_configuration = (id) => {
      if (id === null) {
        Notification.error('This report configuration is protected from modifications');
        return $q.reject();
      }
      return $http
        .delete(`/api/v3/report_configurations/${id}/`, {
          params: {
            organization_id: user_service.get_organization().id
          }
        })
        .then((response) => response.data);
    };

    return report_configurations_factory;
  }
]);
