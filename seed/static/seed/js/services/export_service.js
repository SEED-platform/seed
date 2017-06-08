/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
// dataset services
angular.module('BE.seed.service.export', []).factory('export_service', [
  '$http',
  function ($http) {
    var export_factory = {};

    export_factory.export_buildings = function (buildings_payload) {
      return $http.post(window.BE.urls.export_buildings, buildings_payload).then(function (response) {
        return response.data;
      });
    };
    export_factory.export_buildings_progress = function (export_id) {
      return $http.post(window.BE.urls.export_buildings_progress, {
        export_id: export_id
      }).then(function (response) {
        return response.data;
      });
    };
    export_factory.export_buildings_download = function (export_id) {
      return $http.post(window.BE.urls.export_buildings_download, {
        export_id: export_id
      }).then(function (response) {
        return response.data;
      });
    };

    return export_factory;
  }]);
