/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author Daniel McQuillen
 *
 *  This is an initial cut at making a proper service for Properties in the new "BlueSky" data model.
 *  This class follows how the older building_service worked, except that it mediates actions on "properties"
 *  rather than the older concept of "buildings."
 *
 *
 */
// building services
angular.module('BE.seed.service.property', ['BE.seed.services.label_helper'])
.factory('property_service', [
  '$http',
  '$q',
  'urls',
  'label_helper_service',
  'user_service',
  'generated_urls',
  'spinner_utility',
  function ($http, $q, urls, label_helper_service, user_service, generated_urls, spinner_utility) {

  	var property_factory = { total_number_of_properties_for_user: 0};


    property_factory.get_total_number_of_properties_for_user = function() {
        // django uses request.user for user information
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: window.BE.urls.get_total_number_of_properties_for_user_url
        }).success(function(data, status, headers, config) {
            property_factory.total_number_of_properties_for_user = data.properties_count;
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };


    property_factory.get_property = function(property_id) {
        // django uses request.user for user information
        var defer = $q.defer();
        $http({
            method: 'GET',
            url: window.BE.urls.get_property,
            params: {
                property_id: property_id,
                organization_id: user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };


    property_factory.update_property = function(property, organization_id) {
        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: window.BE.urls.update_property,
            data: {
                property: property,
                organization_id: organization_id
            },
        }).success(function(data, status, headers, config){
            defer.resolve(data);
        }).error(function(data, status, headers, config){
            defer.reject(data, status);
        });
        return defer.promise;
    };


    property_factory.get_columns = function(all_fields) {
        var defer = $q.defer();
        all_fields = all_fields || '';
        $http({
            method: 'GET',
            url: window.BE.urls.get_columns_url,
            params: {
                all_fields: all_fields,
                organization_id: user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

		property_factory.delete_properties = function(search_payload) {
        spinner_utility.show();
        var defer = $q.defer();
        $http({
            method: 'DELETE',
            url: generated_urls.seed.delete_properties,
            data: {
                organization_id: user_service.get_organization().id,
                search_payload: search_payload
            }
        }).success(function(data, status, headers, config) {
            spinner_utility.hide();
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    };

    return property_factory;
}]);
