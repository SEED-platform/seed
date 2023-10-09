/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.espm', []).factory('espm_service', [
  '$http',
  // eslint-disable-next-line func-names
  function ($http) {
    const get_espm_building_xlsx = (org_id, pm_property_id, espm_username, espm_password) => $http
      .post(
        ['/api/v3/portfolio_manager/', pm_property_id, '/download/?organization_id=', org_id].join(''),
        {
          username: espm_username,
          password: espm_password
        },
        {
          responseType: 'arraybuffer'
        }
      )
      .then((response) => response.data)
      .catch((response) => {
        console.log(`Could not get ESPM building from service with status:${response.status}`);
        return response.data;
      });

    const update_building_with_espm_xlsx = (org_id, cycle_id, property_view_id, mapping_profile, file_data) => {
      const body = new FormData();
      const blob = new Blob([file_data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      body.append('file', blob, ['espm_', new Date().getTime(), '.xlsx'].join(''));
      const headers = { 'Content-Type': undefined };

      return $http
        .put(['/api/v3/properties/', property_view_id, '/update_with_espm/?', 'cycle_id=', cycle_id, '&', 'organization_id=', org_id, '&', 'mapping_profile_id=', mapping_profile].join(''), body, {
          headers
        })
        .then((response) => response.data)
        .catch((response) => response.data);
    };

    const analyses_factory = {
      get_espm_building_xlsx,
      update_building_with_espm_xlsx
    };

    return analyses_factory;
  }
]);
