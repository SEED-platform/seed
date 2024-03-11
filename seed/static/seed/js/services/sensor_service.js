/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.sensor', []).factory('sensor_service', [
  '$http',
  ($http) => {
    const sensor_factory = {};

    sensor_factory.get_data_loggers = (property_view_id, organization_id) => $http.get('/api/v3/data_loggers/', { params: { property_view_id, organization_id } }).then((response) => response.data);

    sensor_factory.create_data_logger = (property_view_id, organization_id, display_name, location_description, manufacturer_name, model_name, serial_number, identifier) => $http({
      url: '/api/v3/data_loggers/',
      method: 'POST',
      params: { property_view_id, organization_id },
      data: {
        display_name,
        location_description,
        manufacturer_name,
        model_name,
        serial_number,
        identifier
      }
    }).then((response) => response.data);


    sensor_factory.update_data_logger = (organization_id, id, display_name, location_description, manufacturer_name, model_name, serial_number, identifier) => {
      let url = `/api/v3/data_loggers/${id}/?organization_id=${organization_id}`;
      return $http({
        url: url,
        method: 'PUT',
        data: {
          display_name,
          location_description,
          manufacturer_name,
          model_name,
          serial_number,
          identifier
        }
      }).then((response) => response.data);
    };

    sensor_factory.delete_data_logger = (data_logger_id, organization_id) => {
      let url = `/api/v3/data_loggers/${data_logger_id}?organization_id=${organization_id}`;
      return $http.delete(url).then(resp => resp.data);
    };

    sensor_factory.delete_sensor = (view_id, sensor_id, organization_id) => {
      let url = `/api/v3/properties/${view_id}/sensors/${sensor_id}?organization_id=${organization_id}`;
      return $http.delete(url).then(resp => resp.data);
    };

    sensor_factory.get_sensors = (property_view_id, organization_id) => $http.get(`/api/v3/properties/${property_view_id}/sensors/`, { params: { organization_id } }).then((response) => response.data);

    sensor_factory.property_sensor_usage = (property_view_id, organization_id, interval, showOnlyOccupiedReadings, excluded_sensor_ids, page, per_page) => {
      if (_.isUndefined(excluded_sensor_ids)) excluded_sensor_ids = [];
      let url = `/api/v3/properties/${property_view_id}/sensors/usage/?organization_id=${organization_id}`;
      if (page != null) {
        url += `&page=${page}`;
      }
      if (per_page != null) {
        url += `&per_page=${per_page}`;
      }
      return $http
        .post(url, {
          interval,
          excluded_sensor_ids,
          showOnlyOccupiedReadings
        })
        .then((response) => response.data);
    };

    return sensor_factory;
  }
]);
