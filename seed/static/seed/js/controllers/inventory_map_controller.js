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

      $scope.geocoded_data = $scope.data.filter(building => building.long_lat);
      $scope.ungeocoded_data = $scope.data.filter(building => !building.long_lat);

      // Define base map layer
      var raster = new ol.layer.Tile({
        source: new ol.source.OSM()
      });

      //Define points/pins layer
      var point_style = new ol.style.Style({
        image: new ol.style.Icon({
          src: urls.static_url + "seed/images/map_pin.png",
          scale: 0.075,
          anchor: [0.5, 1]
        })
      });

      var buildingPoint = function (building) {
        var format = new ol.format.WKT();

        var long_lat = building.long_lat
        return format.readFeature(long_lat, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857'
        });
      };

      var pointSources = function (records = $scope.geocoded_data) {
        var features = _.map(records, buildingPoint);

        return new ol.source.Vector({ features: features });
      };

      $scope.map_points = new ol.layer.Vector({
        source: pointSources(),
        style: point_style
      });

      // Define map with layers
      $scope.map = new ol.Map({
        target: 'map',
        layers: [raster, $scope.map_points]
      });

      // Set initial zoom and center
      var getPointsExtent = function () {
        return $scope.map_points.getSource().getExtent();
      };
      var view_options = {
        size: $scope.map.getSize(),
        padding: [10, 10, 10, 10],
      };
      $scope.map.getView().fit(getPointsExtent(), view_options);

    }]);
