/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.audit_template', []).factory('audit_template_service', [
  '$http',
  ($http) => {
    const audit_template_factory = {};

    audit_template_factory.batch_export_to_audit_template = (org_id, property_view_ids) => $http
      .post(`/api/v3/audit_template/batch_export_to_audit_template/?organization_id=${org_id}`, property_view_ids)
      .then((response) => response.data)
      .catch((response) => response.data);

    audit_template_factory.get_city_submission_xml_and_update = (org_id, city_id, custom_id_1) => $http
      .put(`/api/v3/audit_template/get_city_submission_xml/?organization_id=${org_id}`, { city_id, custom_id_1 })
      .then((response) => response)
      .catch((response) => response);

    audit_template_factory.batch_get_city_submission_xml_and_update = (org_id, view_ids) => $http
      .put(`/api/v3/audit_template/batch_get_city_submission_xml/?organization_id=${org_id}`, { view_ids })
      .then((response) => response)
      .catch((response) => response);

    audit_template_factory.get_audit_template_configs = (org_id) => $http
      .get(`/api/v3/audit_template_configs/?organization_id=${org_id}`)
      .then((response) => response.data.data)
      .catch((response) => response.data.data);

    audit_template_factory.upsert_audit_template_config = (org_id, data, timezone) => {
      data.timezone = timezone;
      return data.id ?
        audit_template_factory.update_audit_template_config(org_id, data) :
        audit_template_factory.create_audit_template_config(org_id, data);
    };

    audit_template_factory.create_audit_template_config = (org_id, data) => $http
      .post(`/api/v3/audit_template_configs/?organization_id=${org_id}`, data)
      .then((response) => response.data.data)
      .catch((response) => response.data.data);

    audit_template_factory.update_audit_template_config = (org_id, data) => $http
      .put(`/api/v3/audit_template_configs/${data.id}/?organization_id=${org_id}`, data)
      .then((response) => response.data.data)
      .catch((response) => response.data);

    return audit_template_factory;
  }
]);
