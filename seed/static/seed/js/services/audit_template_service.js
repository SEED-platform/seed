angular.module('BE.seed.service.audit_template', []).factory('audit_template_service', [
  '$http',
  '$log',
  function (
    $http,
    $log
  ) {

    const get_api_token = function (org_id, org_token, email, password) {
      return $http.get([
        '/api/v3/audit_template/get_api_token/?organization_id=', org_id,
        '&organization_token=', org_token,
        '&email=', email,
        '&password=', password
      ].join('')).then(function (response) {
        return response.data;
      });
    };

    const get_building_xml = function (org_id, audit_template_building_id) {
      return $http.get([
        '/api/v3/audit_template/', audit_template_building_id, '/get_building_xml/?organization_id=', org_id
      ].join('')).then(function (response) {
        return response.data;
      });
    };

    const update_building_with_xml = function (org_id, cycle_id, property_view_id, xml_string) {
      let body = new FormData();
      body.append('file_type', 1);
      binary = '';
      for (var i = 0; i < xml_string.length; i++) {
          binary += xml_string[i].charCodeAt(0).toString(2) + " ";
      }
      body.append('file', binary);  // todo: this isn't working like I thought
      return $http.put([
        '/api/v3/properties/' + property_view_id + '/update_with_building_sync/?cycle_id=' + cycle_id + '&organization_id=' + org_id
      ].join(''), body, {}).then(function (response) {
        return response.data;
      });
    }

    const analyses_factory = {
      'get_api_token': get_api_token,
      'get_building_xml': get_building_xml,
      'update_building_with_xml': update_building_with_xml
    };

    return analyses_factory;
  }]);
