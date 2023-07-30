/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.espm', []).factory('espm_service', [
  '$http',
  '$log',
  function (
    $http,
  ) {

    const get_espm_building_xlsx = function (org_id, pm_property_id, espm_username, espm_password) {
      return $http.post(['/api/v3/portfolio_manager/', pm_property_id, '/download/?organization_id=', org_id].join(''), {
        username: espm_username,
        password: espm_password
      }).then(function (response) {        
        return response.data;
      }).catch(function (response) {
        console.log('Could not get ESPM building from service with status:' + response.status);
        return response.data;
      });
    };

    const update_building_with_espm_xlsx = function (org_id, cycle_id, property_view_id, xml_string) {
      let body = new FormData();
      let blob = new Blob([xml_string], { type: 'text/xml' });
      body.append('file', blob, ['at_', new Date().getTime(), '.xml'].join(''));
      body.append('file_type', 1);
      let headers = { 'Content-Type': undefined };

      return $http.put([
        '/api/v3/properties/', property_view_id, '/update_with_espm/?',
        'cycle_id=', cycle_id, '&',
        'organization_id=', org_id
      ].join(''), body, { headers: headers },
      ).then(function (response) {
        return response.data;
      }).catch(function (response) {
        return response.data;
      });
    }

    const analyses_factory = {
      'get_espm_building_xlsx': get_espm_building_xlsx,
      'update_building_with_espm_xlsx': update_building_with_espm_xlsx
    };

    return analyses_factory;
  }]);
