/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.audit_template', []).factory('audit_template_service', [
  '$http',
  ($http) => {
    const audit_template_factory = {}

    audit_template_factory.get_building_xml = (org_id, audit_template_building_id) => $http
      .get(['/api/v3/audit_template/', audit_template_building_id, '/get_building_xml/?organization_id=', org_id].join(''))
      .then((response) => response.data)
      .catch((response) => response.data);

    audit_template_factory.batch_get_building_xml_and_update = (org_id, cycle_id, properties) => $http
      .put(['/api/v3/audit_template/batch_get_building_xml/?organization_id=', org_id, '&cycle_id=', cycle_id].join(''), properties)
      .then((response) => response.data)
      .catch((response) => response.data);

    audit_template_factory.get_buildings = (org_id, cycle_id) => $http
      .get(['/api/v3/audit_template/get_buildings/?organization_id=', org_id, '&cycle_id=', cycle_id].join(''))
      .then((response) => response.data)
      .catch((response) => response.data);

    audit_template_factory.update_building_with_xml = (org_id, cycle_id, property_view_id, audit_template_building_id, xml_string) => {
      const body = new FormData();
      const blob = new Blob([xml_string], { type: 'text/xml' });
      const title = `at_${audit_template_building_id}_${moment().format('YYYYMMDD_HHmmss')}.xml`;
      body.append('file', blob, title);
      body.append('file_type', 1);
      const headers = { 'Content-Type': undefined };

      return $http
        .put(['/api/v3/properties/', property_view_id, '/update_with_building_sync/?', 'cycle_id=', cycle_id, '&', 'organization_id=', org_id].join(''), body, { headers })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    audit_template_factory.batch_export_to_audit_template = (org_id, property_view_ids) => $http
      .post(`/api/v3/audit_template/batch_export_to_audit_template/?organization_id=${org_id}`, property_view_ids)
      .then((response) => response.data)
      .catch((response) => response.data);

    audit_template_factory.batch_get_city_submission_xml_and_update = (org_id, city_id) => $http
      .put(`/api/v3/audit_template/batch_get_city_submission_xml/?organization_id=${org_id}`, {city_id: city_id})
      .then((response) => response)
      .catch((response) => response);

    audit_template_factory.get_audit_template_configs = (org_id) => $http
      .get(`/api/v3/audit_template_configs/?organization_id=${org_id}`)
      .then((response) => response.data.data)
      .catch((response) => response.data.data);

    audit_template_factory.upsert_audit_template_config = (org_id, data, timezone) => {
      data['timezone'] = timezone;
      return data.id 
        ? audit_template_factory.update_audit_template_config(org_id, data)
        : audit_template_factory.create_audit_template_config(org_id, data)
    };

    audit_template_factory.create_audit_template_config = (org_id, data) => $http
      .post(`/api/v3/audit_template_configs/?organization_id=${org_id}`, data)
      .then((response) => {
        console.log('service', response)
        return response.data.data
      })
      .catch((response) => {
        console.log('service fail', response)
        return response.data.data
      });

    audit_template_factory.update_audit_template_config = (org_id, data) => $http
        .put(`/api/v3/audit_template_configs/${data.id}/?organization_id=${org_id}`, data)
        .then((response) => response.data.data)
        .catch((response) => response.data);

    audit_template_factory.delete_audit_template_config = (org_id, config_id) => $http
      .delete(`/api/v3/audit_template_configs/${config_id}/?organization_id=${org_id}`)
      .then((response) => response.data)
      .catch((response) => response.data);

    return audit_template_factory;
  }
]);
