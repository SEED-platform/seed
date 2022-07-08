/**
 * :copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.data_aggregation', []).factory('data_aggregation_service', [
    '$http',
    function ($http) {
        const data_aggregation_factory = {};

        data_aggregation_factory.create_data_aggregation = (organization_id, data) => {
            let { name, type, column } = data
            column = column.id
            return $http({
                url: '/api/v3/data_aggregations/',
                method: 'POST',
                params: {organization_id},
                data: {name, type, column},
            }).then(response => {
                return response.data
            })
        }

        data_aggregation_factory.get_data_aggregations = (organization_id) => {
            return $http({
                url: '/api/v3/data_aggregations/',
                method: 'GET',
                params: {organization_id},
            }).then(response => {
                return response.data
            })
        }

        data_aggregation_factory.get_data_aggregation = (organization_id, data_aggregation_id) => {
            return $http({
                url: `/api/v3/data_aggregations/${data_aggregation_id}/`,
                method: 'GET',
                params: {organization_id},
            }).then(response => {
                return response.data
            })
        }

        data_aggregation_factory.delete_data_aggregation = (organization_id, data_aggregation_id) => {
            return $http({
                url: `/api/v3/data_aggregations/${data_aggregation_id}/`,
                method: 'DELETE',
                params: { organization_id }
            }).then(response => {
                return response.data
            })
        }

        data_aggregation_factory.update_data_aggregation = (organization_id, data_aggregation_id, data) => {
            let  { name, type, column } = data
            column = column.id
            return $http({
                url: `/api/v3/data_aggregations/${data_aggregation_id}/`,
                method: 'PUT',
                params: {organization_id},
                data: {name, type, column}
            }).then(response => {
                return response.data
            })
        }

        data_aggregation_factory.evaluate = (organization_id, data_aggregation_id) => {
            return $http({
                url: `/api/v3/data_aggregations/${data_aggregation_id}/evaluate/`,
                method: 'GET',
                params: {organization_id},
            }).then(response => {
                return response.data
            })
        }

        return data_aggregation_factory
    }]);
