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

    const analyses_factory = {
      'get_api_token': get_api_token,
      'get_building_xml': get_building_xml
    };

    return analyses_factory;
  }]);
