/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.audit_template', []).factory('audit_template_service', [
  '$http',
  '$log',
  function (
    $http,
    $log
  ) {

    const get_building_xml = function (org_id, audit_template_building_id) {
      return $http.get([
        '/api/v3/audit_template/', audit_template_building_id, '/get_building_xml/?organization_id=', org_id
      ].join('')).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    };

    const batch_get_building_xml_and_update = function (org_id, cycle_id, properties) {
      return $http.put([
        '/api/v3/audit_template/batch_get_building_xml/?organization_id=', org_id, '&cycle_id=', cycle_id
      ].join(''), properties).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    }

    const get_buildings = function (org_id, cycle_id) {
      return $http.get([
        '/api/v3/audit_template/get_buildings/?organization_id=', org_id, '&cycle_id=', cycle_id
      ].join('')).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data
      })
    }

    const update_building_with_xml = function (org_id, cycle_id, property_view_id, audit_template_building_id, xml_string) {
      let body = new FormData();
      let blob = new Blob([xml_string], {type: 'text/xml'});
      let title = `at_${audit_template_building_id}_${moment().format('YYYYMMDD_HHmmss')}.xml`
      body.append('file', blob, title);
      body.append('file_type', 1);
      let headers = {'Content-Type': undefined};

      return $http.put([
          '/api/v3/properties/', property_view_id, '/update_with_building_sync/?',
          'cycle_id=', cycle_id, '&', 'organization_id=', org_id
        ].join(''), body, {headers: headers},
      ).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    }

    const batch_export_to_audit_template = function (org_id, property_view_ids) {
      return $http.post(
        `/api/v3/audit_template/batch_export_to_audit_template/?organization_id=${org_id}`,
        property_view_ids).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data
      })
    }

    const analyses_factory = {
      'get_building_xml': get_building_xml,
      'batch_get_building_xml_and_update': batch_get_building_xml_and_update,
      'get_buildings': get_buildings,
      'update_building_with_xml': update_building_with_xml,
      'export_to_audit_template': batch_export_to_audit_template,
    };

    return analyses_factory;
  }]);
