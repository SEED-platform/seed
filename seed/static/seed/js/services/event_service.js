/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.event', []).factory('event_service', [
    '$http',
    function ($http) {

        const event_factory = {};

        event_factory.get_events = function (org_id, inventory_type, property_pk) {
            return $http.get('/api/v3/' + inventory_type + '/' + property_pk + '/events/', {
                params: {
                    organization_id: org_id
                }
            }).then(function (response) {
                return response.data;
            });
        };


        return event_factory;

    }]);
