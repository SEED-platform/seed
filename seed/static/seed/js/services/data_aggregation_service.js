/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.data_aggregation', []).factory('data_aggregation_service', [
    '$http',
    function ($http) {
        const data_aggregation_factory = {};

        data_aggregation_factory.create_data_aggregation = function (organization_id, data) {
            console.log('create data', data)
            return $http({
                url: '/api/v3/data_aggregations/',
                method: 'POST',
                params: {organization_id},
                data: data,
            }).then(function (response) {
                return response.data
            })
        }

        return data_aggregation_factory
    }]);