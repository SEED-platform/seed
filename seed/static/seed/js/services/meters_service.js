angular.module('BE.seed.service.meters', [])
  .factory('meters_service', [
    '$http',
    function ($http) {
      var meters_factory = {};

      meters_factory.parsed_type_units = function (file_id, org_id) {
        return $http.post('/api/v2/meters/parsed_meters_confirmation/', {
          file_id: file_id,
          organization_id: org_id
        }).then(function (response) {
          return response.data;
        });
      };

      return meters_factory;
    }
  ]);
