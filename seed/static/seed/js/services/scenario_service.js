/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
