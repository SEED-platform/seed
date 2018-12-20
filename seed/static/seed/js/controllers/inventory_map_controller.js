/**
 * :copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_map', [])
  .controller('inventory_map_controller', [
    '$scope',
    '$stateParams',
    'inventory',
    'inventory_service',
    'labels',
    'urls',
    'spinner_utility',
    function ($scope,
              $stateParams,
              inventory,
              inventory_service,
              labels,
              urls,
              spinner_utility) {
      spinner_utility.show();

      $scope.inventory_type = $stateParams.inventory_type;
      $scope.data = inventory.results;

      $scope.geocoded_data = _.filter($scope.data, function(building) {
        return building.long_lat
      });
      $scope.ungeocoded_data = _.filter($scope.data, function(building) {
        return !building.long_lat
      });

      // Define base map layer
      var raster = new ol.layer.Tile({
        source: new ol.source.OSM()
      });

      // Define points/pins layer
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
        var feature = format.readFeature(long_lat, {
          dataProjection: 'EPSG:4326',
          featureProjection: 'EPSG:3857'
        });

        feature.setProperties(building)
        return feature
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

      // Find area of given points or null if no points
      var getPointsExtent = function () {
        var points_source = $scope.map_points.getSource();

        if (points_source.isEmpty()) {
          return null;
        } else {
          return $scope.map_points.getSource().getExtent();
        };
      };

      // Set initial zoom and center
      if (getPointsExtent()) {
        var view_options = {
          size: $scope.map.getSize(),
          padding: [10, 10, 10, 10],
        };
        $scope.map.getView().fit(getPointsExtent(), view_options);
      } else {
        // Default view with no points is the middle of US
        var empty_view = new ol.View ({
          center: ol.proj.fromLonLat([-99.066067, 39.390897]),
          zoom: 4.5,
        })
        $scope.map.setView(empty_view);
      };

      var rerenderPoints = function (records) {
        $scope.map_points.setSource(pointSources(records));
        // TODO: Decide if we want to rezoom and recenter map
        // $scope.map.getView().fit(getPointsExtent(), view_options);
      };

      // Labels
      // Reduce labels to only records found in the current cycle
      $scope.selected_labels = [];
      updateApplicableLabels();

      var localStorageLabelKey = 'grid.' + $scope.inventory_type + '.labels';

      // Reapply valid previously-applied labels
      var ids = inventory_service.loadSelectedLabels(localStorageLabelKey);
      $scope.selected_labels = _.filter($scope.labels, function (label) {
        return _.includes(ids, label.id);
      });

      $scope.clear_labels = function () {
        $scope.selected_labels = [];
      };

      $scope.loadLabelsForFilter = function (query) {
        return _.filter($scope.labels, function (lbl) {
          if (_.isEmpty(query)) {
            // Empty query so return the whole list.
            return true;
          } else {
            // Only include element if its name contains the query string.
            return _.includes(_.toLower(lbl.name), _.toLower(query));
          }
        });
      };

      function updateApplicableLabels() {
        var inventoryIds;
        if ($scope.inventory_type === 'properties') {
          inventoryIds = _.map($scope.data, 'property_view_id').sort();
        } else {
          inventoryIds = _.map($scope.data, 'taxlot_view_id').sort();
        }
        $scope.labels = _.filter(labels, function (label) {
          return _.some(label.is_applied, function (id) {
            return _.includes(inventoryIds, id);
          });
        });
        // Ensure that no previously-applied labels remain
        var new_labels = _.filter($scope.selected_labels, function (label) {
          return _.includes($scope.labels, label.id);
        });
        if ($scope.selected_labels.length !== new_labels.length) {
          $scope.selected_labels = new_labels;
        }
      }

      var filterUsingLabels = function () {
        // Only submit the `id` of the label to the API.
        var ids;
        if ($scope.labelLogic === 'and') {
          ids = _.intersection.apply(null, _.map($scope.selected_labels, 'is_applied'));
        } else if (_.includes(['or', 'exclude'], $scope.labelLogic)) {
          ids = _.union.apply(null, _.map($scope.selected_labels, 'is_applied'));
        }

        inventory_service.saveSelectedLabels(localStorageLabelKey, _.map($scope.selected_labels, 'id'));

        if (_.isEmpty(ids)) {
          rerenderPoints($scope.geocoded_data)
        } else {
          var filtered_records = _.filter($scope.geocoded_data, function (record) {
            return _.includes(ids,record.id);
          });
          rerenderPoints(filtered_records);
        }
      };

      $scope.labelLogic = localStorage.getItem('labelLogic');
      $scope.labelLogic = _.includes(['and', 'or', 'exclude'], $scope.labelLogic) ? $scope.labelLogic : 'and';
      $scope.labelLogicUpdated = function (labelLogic) {
        $scope.labelLogic = labelLogic;
        localStorage.setItem('labelLogic', $scope.labelLogic);
        filterUsingLabels();
      };

      $scope.$watchCollection('selected_labels', filterUsingLabels);

    }]);
