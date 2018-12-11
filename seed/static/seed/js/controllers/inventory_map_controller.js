/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_map', [])
  .controller('inventory_map_controller', [
    '$scope',
    '$stateParams',
    'inventory',
    'urls',
    'spinner_utility',
    function ($scope,
              $stateParams,
              inventory,
              urls,
              spinner_utility) {
      spinner_utility.show();

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.data = inventory.results;
      $scope.pagination = inventory.pagination;

      $scope.geocoded_data = $scope.data.filter(building => building.long_lat);
      $scope.ungeocoded_data = $scope.data.filter(building => !building.long_lat);

      // Render Map
      var renderMap = function () {
        var raster = new ol.layer.Tile({
          source: new ol.source.OSM()
        });

        var vector_style = new ol.style.Style({
          image: new ol.style.Icon({
            src: urls.static_url + "seed/images/map_pin.png",
            scale: 0.075,
            anchor: [0.5, 1]
          })
        });

        var vectors = new ol.layer.Vector({
          source: vectorSources(),
          style: vector_style
        });

        // TODO: Consider making center be the centroid of shown points
        // and make zoom dynamic (just large enough to see all points)
        center_zoom = {
          center: ol.proj.fromLonLat([-104.986292, 39.765566]),
          zoom: 4
        };

        var map = new ol.Map({
          target: 'map',
          layers: [raster, vectors],
          view: new ol.View(center_zoom)
        });
      };

      var vectorSources = function () {
        var features = _.map($scope.geocoded_data, buildingPoint);

        return new ol.source.Vector({ features: features });
      };

      var buildingPoint = function (building) {
        var format = new ol.format.WKT();

        var long_lat = building.long_lat
        return format.readFeature(long_lat, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857'
        });

      };

      renderMap();

    }]);
