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

    const batch_get_building_xml = function (org_id, properties) {
      return $http.put([
        '/api/v3/audit_template/batch_get_building_xml/?organization_id=', org_id
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

    const update_building_with_xml = function (org_id, cycle_id, property_view_id, xml_string) {
      let body = new FormData();
      let blob = new Blob([xml_string], {type: 'text/xml'});
      body.append('file', blob, ['at_', new Date().getTime() , '.xml'].join(''));
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

    const batch_update_with_xml = function (org_id, cycle_id, property_xmls) {
      bodies = new FormData();
      property_xmls.forEach(data => {
        let blob = new Blob([data.xml], { type: 'text/xml' });
        bodies.append('files', blob, ['at_', new Date().getTime(), '.xml'].join(''));
        bodies.append('file_types', 1);
        bodies.append('property_views', data.property_view)
      })
      let headers = { 'Content-Type': undefined };

      return $http.put([
        '/api/v3/properties/batch_update_with_building_sync/?',
        'cycle_id=', cycle_id, '&', 'organization_id=', org_id
      ].join(''), bodies, { headers: headers },
      ).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    }

    const analyses_factory = {
      'get_building_xml': get_building_xml,
      'batch_get_building_xml': batch_get_building_xml,
      'get_buildings': get_buildings,
      'update_building_with_xml': update_building_with_xml,
      'batch_update_with_xml': batch_update_with_xml
    };

    return analyses_factory;
  }]);
