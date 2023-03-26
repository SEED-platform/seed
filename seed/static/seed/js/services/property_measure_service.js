/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
