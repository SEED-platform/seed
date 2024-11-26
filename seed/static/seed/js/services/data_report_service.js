/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.data_report', []).factory('data_report_service', [
    '$http',
    'user_service',
    (
        $http,
        user_service
    ) => {
        const data_report_service = {};

        data_report_service.get_data_reports = () => $http.get('/api/v3/data_reports/', {
            params: {
                organization_id: user_service.get_organization().id
            }
        })
        .then((response) => response.data)
        .catch((response) => response)

        data_report_service.create_data_report = (data_report) => $http.post('/api/v3/data_reports/', data_report)
        .then((response) => response.data)
        .catch((response) => response)

        data_report_service.update_data_report = (data_report) => $http.put(`/api/v3/data_reports/${data_report.id}/`, data_report)
        .then((response) => response.data)
        .catch((response) => response)

        data_report_service.delete_data_report = (data_report_id) => $http.delete(`/api/v3/data_reports/${data_report_id}/`, {
            params: {
                organization: user_service.get_organization().id
            }
        })
        .then((response) => response)
        .catch((response) => response)

        data_report_service.get_portfolio_summary = (data_report_id) => $http.get(`/api/v3/data_reports/${data_report_id}/portfolio_summary/`, {
            params: {
                organization_id: user_service.get_organization().id
            }
        })
        .then((response) => response)
        .catch((response) => response)

        return data_report_service
    }
]);
