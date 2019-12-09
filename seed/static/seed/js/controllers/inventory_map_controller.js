/**
 * :copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_map', [])
  .controller('inventory_map_controller', [
    '$scope',
    '$stateParams',
    '$state',
    '$log',
    '$uibModal',
    'cycles',
    'inventory_service',
    'labels',
    'urls',
    function (
      $scope,
      $stateParams,
      $state,
      $log,
      $uibModal,
      cycles,
      inventory_service,
      labels,
      urls
    ) {
      // always map properties with taxlot in the 'related' field
      $scope.inventory_type = 'properties';
      //$scope.inventory_type = $stateParams.inventory_type;

      $scope.data = [];
      $scope.geocoded_data = [];
      $scope.ungeocoded_data = [];

      var lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: lastCycleId ? _.find(cycles.cycles, {id: lastCycleId}) : _.first(cycles.cycles),
        cycles: cycles.cycles
      };

      var fetch = function (page, chunk) {
        // console.log('Fetching page ' + page + ' (chunk size ' + chunk + ')');
        return inventory_service.get_properties(page, chunk, undefined, undefined).then(function (data) {
          $scope.progress = {
            current: data.pagination.end,
            total: data.pagination.total,
            percent: Math.round(data.pagination.end / data.pagination.total * 100)
          };
          if (data.pagination.has_next) {
            return fetch(page + 1, chunk).then(function (data2) {
              return data.results.concat(data2);
            });
          }
          return data.results;
        });
      };

      var page = 1;
      var chunk = 5000;
      $scope.progress = {};
      var modalInstance = $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/inventory_loading_modal.html',
        backdrop: 'static',
        windowClass: 'inventory-progress-modal',
        scope: $scope
      });
      return fetch(page, chunk).then(function (data) {
        modalInstance.close();

        $scope.data = data;
        $scope.geocoded_data = _.filter($scope.data, 'long_lat');
        $scope.ungeocoded_data = _.reject($scope.data, 'long_lat');
        // buildings with UBID bounding boxes
        $scope.bb_data = _.filter($scope.data, 'bounding_box');

        var geocodedTaxlots = function (properties_data) {
          var taxlots = [];
          _.each(properties_data, function (record) {
            if (!_.isUndefined(record.related) && !_.isEmpty(record.related)) {
              // getting the ones with bounding boxes not long_lat
              // since we are not interested in mapping points for taxlots
              var bb_taxlots = _.filter(record.related, 'bounding_box');
              taxlots = _.concat(taxlots, bb_taxlots);
            }
          });
          return _.uniqBy(taxlots, 'id');
        };

        // extract related taxlots from building inventory
        $scope.taxlots = geocodedTaxlots($scope.data);
        // $log.log('taxlots: ', $scope.taxlots);

        // store a mapping of layers z-index and visibility
        $scope.layers = {};
        $scope.layers.base_layer = {zIndex: 0, visible: 1};
        $scope.layers.hexbin_layer = {zIndex: 1, visible: 1};
        $scope.layers.points_layer = {zIndex: 2, visible: 1};
        $scope.layers.building_bb_layer = {zIndex: 3, visible: 1};
        $scope.layers.building_centroid_layer = {zIndex: 4, visible: 1};
        $scope.layers.taxlot_bb_layer = {zIndex: 5, visible: 0};
        $scope.layers.taxlot_centroid_layer = {zIndex: 6, visible: 0};

        // Map
        var base_layer = new ol.layer.Tile({
          source: new ol.source.Stamen({
            layer: 'terrain'
          }),
          zIndex: $scope.layers.base_layer.zIndex // Note: This is used for layer toggling.
        });


        // Define buildings source - the basis of layers
        var buildingPoint = function (building) {
          var format = new ol.format.WKT();

          var long_lat = building.long_lat;
          var feature = format.readFeature(long_lat, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });

          feature.setProperties(building);
          return feature;
        };

        var buildingSources = function (records) {
          if (_.isUndefined(records)) records = $scope.geocoded_data;
          var features = _.map(records, buildingPoint);

          return new ol.source.Vector({features: features});
        };

        // Define building UBID bounding box
        var buildingBB = function (building) {
          var format = new ol.format.WKT();

          var bounding_box = building.bounding_box;
          var feature = format.readFeature(bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(building);
          return feature;
        };

        // Define building UBID centroid box
        var buildingCentroid = function (building) {
          var format = new ol.format.WKT();

          var bounding_box = building.centroid;
          var feature = format.readFeature(bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(building);
          return feature;
        };

        var buildingBBSources = function (records) {
          if (_.isUndefined(records)) records = $scope.bb_data;
          var features = _.map(records, buildingBB);

          return new ol.source.Vector({features: features});
        };

        var buildingCentroidSources = function (records) {
          if (_.isUndefined(records)) records = $scope.bb_data;
          var features = _.map(records, buildingCentroid);

          return new ol.source.Vector({features: features});
        };

        // Define taxlot ULID bounding box
        var taxlotBB = function (taxlot) {
          var format = new ol.format.WKT();

          var bounding_box = taxlot.bounding_box;
          var feature = format.readFeature(bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(taxlot);
          return feature;
        };

        // Define taxlot ULID centroid box
        var taxlotCentroid = function (taxlot) {
          var format = new ol.format.WKT();

          var bounding_box = taxlot.centroid;
          var feature = format.readFeature(bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(taxlot);
          return feature;
        };

        var taxlotBBSources = function (records) {
          if (_.isUndefined(records)) records = $scope.taxlots;
          var features = _.map(records, taxlotBB);

          return new ol.source.Vector({features: features});
        };

        var taxlotCentroidSources = function (records) {
          if (_.isUndefined(records)) records = $scope.taxlots;
          var features = _.map(records, taxlotCentroid);

          return new ol.source.Vector({features: features});
        };

        // Points/clusters layer
        var clusterPointStyle = function (size) {
          var relative_radius = 10 + Math.min(7, size / 50);
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
              fill: new ol.style.Fill({color: '#fff'})
            })
          });
        };

        var singlePointStyle = function () {
          return new ol.style.Style({
            image: new ol.style.Icon({
              src: urls.static_url + 'seed/images/map_pin.png',
              scale: 0.05,
              anchor: [0.5, 1]
            })
          });
        };

        var clusterSource = function (records) {
          if (_.isUndefined(records)) records = $scope.geocoded_data;
          return new ol.source.Cluster({
            source: buildingSources(records),
            distance: 45
          });
        };

        var pointsLayerStyle = function (feature) {
          var size = feature.get('features').length;
          if (size > 1) {
            return clusterPointStyle(size);
          } else {
            return singlePointStyle();
          }
        };

        // style for building ubid bounding and centroid boxes
        var buildingStyle = function (/*feature*/) {
          return new ol.style.Style({
            stroke: new ol.style.Stroke({
              color: '#185189',
              width: 2
            })
          });
        };

        // style for taxlot ulid bounding and centroid boxes
        var taxlotStyle = function (/*feature*/) {
          return new ol.style.Style({
            stroke: new ol.style.Stroke({
              color: '#10A0A0',
              width: 2
            })
          });
        };

        $scope.points_layer = new ol.layer.Vector({
          source: clusterSource(),
          zIndex: $scope.layers.points_layer.zIndex, // Note: This is used for layer toggling.
          style: pointsLayerStyle
        });

        $scope.building_bb_layer = new ol.layer.Vector({
          source: buildingBBSources(),
          zIndex: $scope.layers.building_bb_layer.zIndex,
          style: buildingStyle
        });

        $scope.building_centroid_layer = new ol.layer.Vector({
          source: buildingCentroidSources(),
          zIndex: $scope.layers.building_centroid_layer.zIndex,
          style: buildingStyle
        });

        $scope.taxlot_bb_layer = new ol.layer.Vector({
          source: taxlotBBSources(),
          zIndex: $scope.layers.taxlot_bb_layer.zIndex,
          style: taxlotStyle
        });

        $scope.taxlot_centroid_layer = new ol.layer.Vector({
          source: taxlotCentroidSources(),
          zIndex: $scope.layers.taxlot_centroid_layer.zIndex,
          style: taxlotStyle
        });

        // Hexbin layer
        var hexagon_size = 750;

        var hexbinSource = function (records) {
          if (_.isUndefined(records)) records = $scope.geocoded_data;
          return new ol.source.HexBin(
            {
              source: buildingSources(records),
              size: hexagon_size
            }
          );
        };

        $scope.hexbin_color = [75, 0, 130];
        var hexbin_max_opacity = 0.8;
        var hexbin_min_opacity = 0.2;

        $scope.hexbinInfoBarColor = function () {
          var hexbin_color_code = $scope.hexbin_color.join(',');
          var left_color = 'rgb(' + hexbin_color_code + ',' + hexbin_max_opacity * hexbin_min_opacity + ')';
          var right_color = 'rgb(' + hexbin_color_code + ',' + hexbin_max_opacity + ')';

          return {
            background: 'linear-gradient(to right, ' + left_color + ', ' + right_color + ')'
          };
        };

        var hexagonStyle = function (opacity) {
          var color = $scope.hexbin_color.concat([opacity]);
          return [
            new ol.style.Style({
              fill: new ol.style.Fill({color: color})
            })
          ];
        };

        var hexbinStyle = function (feature) {
          var features = feature.getProperties().features;
          var site_eui_key = _.find(_.keys(features[0].values_), function (key) {
            return _.startsWith(key, 'site_eui');
          });
          var site_euis = _.map(features, function (point) {
            return point.values_[site_eui_key];
          });
          var total_eui = _.sum(site_euis);
          var opacity = Math.max(hexbin_min_opacity, total_eui / hexagon_size);

          return hexagonStyle(opacity);
        };

        $scope.hexbin_layer = new ol.layer.Vector({
          source: hexbinSource(),
          zIndex: $scope.layers.hexbin_layer.zIndex, // Note: This is used for layer toggling.
          opacity: hexbin_max_opacity,
          style: hexbinStyle
        });

        // Render map
        // start with taxlot layers off
        $scope.map = new ol.Map({
          target: 'map',
          layers: [base_layer, $scope.hexbin_layer, $scope.points_layer, $scope.building_bb_layer, $scope.building_centroid_layer]
        });

        // Toggle layers

        // If a layer's z-index is changed, it should be changed here as well.
        var layer_at_z_index = {
          0: base_layer,
          1: $scope.hexbin_layer,
          2: $scope.points_layer,
          3: $scope.building_bb_layer,
          4: $scope.building_centroid_layer,
          5: $scope.taxlot_bb_layer,
          6: $scope.taxlot_centroid_layer
        };

        $scope.layerVisible = function (z_index) {
          var layers = $scope.map.getLayers().array_;
          var z_indexes = _.map(layers, function (layer) {
            return layer.values_.zIndex;
          });
          return z_indexes.includes(z_index);
        };

        $scope.toggle_layer = function (z_index) {
          if ($scope.layerVisible(z_index)) {
            $scope.map.removeLayer(layer_at_z_index[z_index]);
          } else {
            $scope.map.addLayer(layer_at_z_index[z_index]);
          }
        };

        // Popup
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

        var detailPageIcon = function (point_info) {
          var link_html = '';
          var icon_html = '<i class="ui-grid-icon-info-circled"></i>';

          if ($scope.inventory_type === 'properties') {
            link_html = '<a href="#/properties/' +
              point_info.property_view_id +
              '">' +
              icon_html +
              '</a>';
          } else {
            link_html = '<a href="#/taxlots/' +
              point_info.property_view_id +
              '">' +
              icon_html +
              '</a>';
          }

          return link_html;
        };

        var showPointInfo = function (point) {
          var pop_info = point.getProperties();
          var address_line_1_key = _.find(_.keys(pop_info), function (key) {
            return _.startsWith(key, 'address_line_1');
          });

          var coordinates = point.getGeometry().getCoordinates();

          popup_overlay.setPosition(coordinates);
          $(popup_element).popover({
            placement: 'top',
            html: true,
            selector: true,
            content: pop_info[address_line_1_key] + detailPageIcon(pop_info)
          });

          $(popup_element).popover('show');
          popupShown = true;
        };

        // Define point/cluster click event - default is no popup shown
        var popupShown = false;

        $scope.map.on('click', function (event) {
          var points = [];

          $scope.map.forEachFeatureAtPixel(event.pixel, function (feature) {
            // If feature has a center (implies it is a hexbin), disregard click
            if (feature.getKeys().includes('center')) {
              return;
            }
            points = feature.get('features');
          });

          if (popupShown) {
            $(popup_element).popover('destroy');
            popupShown = false;
          } else if (points && points.length == 1) {
            showPointInfo(points[0]);
          } else if (points && points.length > 1) {
            zoomOnCluster(points);
          }
        });

        var zoomOnCluster = function (points) {
          var source = new ol.source.Vector({features: points});
          zoomCenter(source, {duration: 750});
        };

        // Zoom and center based on provided points (none, all, or a subset)
        var zoomCenter = function (points_source, extra_view_options) {
          if (_.isUndefined(extra_view_options)) extra_view_options = {};
          if (points_source.isEmpty()) {
            // Default view with no points is the middle of US
            var empty_view = new ol.View({
              center: ol.proj.fromLonLat([-99.066067, 39.390897]),
              zoom: 4.5
            });
            $scope.map.setView(empty_view);
          } else {
            var extent = points_source.getExtent();
            var view_options = Object.assign({
              size: $scope.map.getSize(),
              padding: [10, 10, 10, 10]
            }, extra_view_options);
            $scope.map.getView().fit(extent, view_options);
          }
        };

        // Set initial zoom and center
        zoomCenter(clusterSource().getSource());

        var rerenderPoints = function (records) {
          $scope.points_layer.setSource(clusterSource(records));
          $scope.hexbin_layer.setSource(hexbinSource(records));
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
              return _.includes(ids, record.id);
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

        var refreshUsingCycle = function () {
          if ($scope.inventory_type === 'properties') {
            $scope.data = inventory_service.get_properties(1, undefined, $scope.cycle.selected_cycle, undefined).results;
            $state.reload();
          } else if ($scope.inventory_type === 'taxlots') {
            $scope.data = inventory_service.get_taxlots(1, undefined, $scope.cycle.selected_cycle, undefined).results;
            $state.reload();
          }
        };

        $scope.update_cycle = function (cycle) {
          inventory_service.save_last_cycle(cycle.id);
          $scope.cycle.selected_cycle = cycle;
          refreshUsingCycle();
        };
      });
    }]);

