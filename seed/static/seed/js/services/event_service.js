/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
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
