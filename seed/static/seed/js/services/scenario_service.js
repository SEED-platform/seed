/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.scenario', []).factory('scenario_service', [
    '$http',
    function ($http) {

        const scenario_service = {};

        scenario_service.delete_scenario = function (organization_id, property_view_id, scenario_id, ) {
            return $http({
                url: `/api/v3/properties/${property_view_id}/scenarios/${scenario_id}/`,
                method: 'DELETE',
            }).then(response => {
                return response.data
            })
        }

        return scenario_service;
    }]);
