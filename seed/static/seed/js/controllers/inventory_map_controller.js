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

      var base_layer = new ol.layer.Tile({
        source: new ol.source.Stamen({
          layer: 'terrain'
        })
      });

      var clusterPointStyle = function (size) {
        // TODO revisit this with a larger dataset
        // point radius of each cluster icon is relative to size and has a min and max.
        var relative_radius = 10 + Math.min(7, size/50)
        return new ol.style.Style({
          image: new ol.style.Circle({
            radius: relative_radius,
            stroke: new ol.style.Stroke({
              color: '#fff'
            }),
            fill: new ol.style.Fill({
              color: '#3399CC'
            })
          }),
          text: new ol.style.Text({
            text: size.toString(),
            fill: new ol.style.Fill({ color: '#fff' })
          })
        });
      };

      var singlePointStyle = function () {
        return new ol.style.Style({
          image: new ol.style.Icon({
            src: urls.static_url + "seed/images/map_pin.png",
            scale: 0.05,
            anchor: [0.5, 1],
          })
        });
      };

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

      var clusterSource = function (records = $scope.geocoded_data) {
        return new ol.source.Cluster({
          source: pointSources(records),
          distance: 45,
        });
      };

      // Define points/clusters layer
      $scope.points_layer = new ol.layer.Vector({
        source: clusterSource(),
        style: function(feature) {
          var size = feature.get('features').length;
          if (size > 1) {
            return clusterPointStyle(size)
          } else {
            return singlePointStyle();
          };
        }
      });

      $scope.map = new ol.Map({
        target: 'map',
        layers: [base_layer, $scope.points_layer]
      });

      // Building Popup
      var popup_element = document.getElementById('popup-element');

      // Define overlay attaching html element
      var popup_overlay = new ol.Overlay({
        element: popup_element,
        positioning: 'bottom-center',
        stopEvent: false,
        autoPan: true,
        autoPanMargin: 75,
        offset: [0, -135]
      });
      $scope.map.addOverlay(popup_overlay);

      var showPointInfo = function (point) {
        var pop_info = point.getProperties();
        var address_line_1_key = _.find(_.keys(pop_info), function(key) {
          return _.startsWith(key, "address_line_1")
        });

        var coordinates = point.getGeometry().getCoordinates();

        popup_overlay.setPosition(coordinates);
        $(popup_element).popover({
          placement: 'top',
          html: true,
          selector: true,
          content: pop_info[address_line_1_key]
        });

        $(popup_element).popover('show');
      };

      // Define point/cluster click event
      // TODO Display info doesn't change bug when popover already shown.
      // TODO cont. Another bug comes up if trying to destroy element before recreate and render
      // TODO cont. set timeout wasn't working as expected??
      $scope.map.on("click", function (event) {
        var points = []

        $scope.map.forEachFeatureAtPixel(event.pixel, function (feature) {
          points = feature.get("features")
        });

        if (points && points.length == 1) {
          showPointInfo(points[0]);
        } else if (points && points.length ) {
          zoomOnCluster(points);
          $(popup_element).popover('destroy');
        } else {
          $(popup_element).popover('destroy');
        }
      });

      var zoomOnCluster = function (points) {
        var source = new ol.source.Vector({ features: points });
        zoomCenter(source, { duration: 750 });
      }

      // Zoom and center based on provided points (none, all, or a subset)
      var zoomCenter = function (points_source, extra_view_options = {}) {
        if (points_source.isEmpty()) {
          // Default view with no points is the middle of US
          var empty_view = new ol.View ({
            center: ol.proj.fromLonLat([-99.066067, 39.390897]),
            zoom: 4.5,
          });
          $scope.map.setView(empty_view);
        } else {
          var extent = points_source.getExtent();
          var view_options = Object.assign({
            size: $scope.map.getSize(),
            padding: [10, 10, 10, 10],
          }, extra_view_options);
          $scope.map.getView().fit(extent, view_options);
        };
      };

      // Set initial zoom and center
      zoomCenter(clusterSource().getSource());

      var rerenderPoints = function (records) {
        $scope.points_layer.setSource(clusterSource(records));
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
        if (_.isEmpty($scope.selected_labels)) {
          return rerenderPoints($scope.geocoded_data);
        }

        // Only submit the `id` of the label to the API.
        var ids;
        if ($scope.labelLogic === 'and') {
          ids = _.intersection.apply(null, _.map($scope.selected_labels, 'is_applied'));
        } else if (_.includes(['or', 'exclude'], $scope.labelLogic)) {
          ids = _.union.apply(null, _.map($scope.selected_labels, 'is_applied'));
        }

        inventory_service.saveSelectedLabels(localStorageLabelKey, _.map($scope.selected_labels, 'id'));

        if (_.isEmpty(ids)) {
          rerenderPoints(ids);
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
