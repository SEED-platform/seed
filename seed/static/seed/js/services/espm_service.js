/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.espm', []).factory('espm_service', [
  '$http',
  '$log',
  function (
    $http
  ) {

    const get_espm_building_xlsx = function (org_id, pm_property_id, espm_username, espm_password) {
      return $http.post(['/api/v3/portfolio_manager/', pm_property_id, '/download/?organization_id=', org_id].join(''), {
        username: espm_username,
        password: espm_password
      }, {
        responseType: 'arraybuffer'
      }).then(function (response) {
        return response.data;
      }).catch(function (response) {
        console.log('Could not get ESPM building from service with status:' + response.status);
        return response.data;
      });
    };

    const update_building_with_espm_xlsx = function (org_id, cycle_id, property_view_id, file_data) {
      let body = new FormData();
      let blob = new Blob([file_data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      body.append('file', blob, ['espm_', new Date().getTime(), '.xlsx'].join(''));
      let headers = {'Content-Type': undefined};

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
    };

    const analyses_factory = {
      get_espm_building_xlsx: get_espm_building_xlsx,
      update_building_with_espm_xlsx: update_building_with_espm_xlsx
    };

    return analyses_factory;
  }]);
