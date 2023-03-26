/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.property_measure', []).factory('property_measure_service', [
    '$http',
    function ($http) {

        const property_measure_factory = {};

        property_measure_factory.delete_property_measure = function (organization_id, property_view_id, scenario_id, property_measure_id) {
            return $http({
                url: `/api/v3/properties/${property_view_id}/scenarios/${scenario_id}/measures/${property_measure_id}/`,
                method: 'DELETE',
            }).then(response => {
                return response.data
            })
        }

        return property_measure_factory;
    }]);
