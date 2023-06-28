/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_map', [])
  .controller('inventory_detail_map_controller', [
    '$scope',
    '$stateParams',
    '$state',
    (
      $scope,
      $stateParams,
      $state
    ) => {
      $scope.inventory_type = $stateParams.inventory_type;

      $scope.geocoded_data = _.filter([$scope.item_state], 'long_lat');
      $scope.ungeocoded_data = _.reject([$scope.item_state], 'long_lat');

      // buildings with UBID bounding boxes and geocoded data
      const geocodedRelated = (data, field) => {
        let related = [];
        _.each(data, record => {
          if (!_.isUndefined(record.related) && !_.isEmpty(record.related)) {
            related = _.concat(related, _.filter(record.related, field));
          }
        });
        return _.uniqBy(related, 'id');
      };
      if ($scope.inventory_type === 'properties') {
        $scope.geocoded_properties = _.filter([$scope.item_state], 'bounding_box');
        $scope.geocoded_taxlots = geocodedRelated([$scope.item_state], 'bounding_box');
      } else {
        $scope.geocoded_properties = geocodedRelated([$scope.item_state], 'bounding_box');
        $scope.geocoded_taxlots = _.filter([$scope.item_state], 'bounding_box');
      }

      $scope.$watch('reload', () => {
        $scope.reload && $state.reload();
      });

      // Controller Init Function
      const init = () => {
        $scope.bounding_box = $scope.item_state.bounding_box.replace(/^SRID=\d+;/, '');
        $scope.centroid = $scope.item_state.centroid.replace(/^SRID=\d+;/, '');

        // store a mapping of layers z-index and visibility
        $scope.layers = {};
        $scope.layers.base_layer = {zIndex: 0, visible: 1};
        if ($scope.inventory_type === 'properties') {
          $scope.layers.points_layer = {zIndex: 2, visible: 1};
          $scope.layers.building_bb_layer = {zIndex: 3, visible: 1};
          $scope.layers.building_centroid_layer = {zIndex: 4, visible: 1};
          $scope.layers.taxlot_bb_layer = {zIndex: 5, visible: 0};
          $scope.layers.taxlot_centroid_layer = {zIndex: 6, visible: 0};
        } else {
          // taxlots
          $scope.layers.points_layer = {zIndex: 2, visible: 1};
          $scope.layers.building_bb_layer = {zIndex: 3, visible: 0};
          $scope.layers.building_centroid_layer = {zIndex: 4, visible: 0};
          $scope.layers.taxlot_bb_layer = {zIndex: 5, visible: 1};
          $scope.layers.taxlot_centroid_layer = {zIndex: 6, visible: 1};
        }

        // Map
        const base_layer = new ol.layer.Tile({
          source: new ol.source.OSM(),
          zIndex: $scope.layers.base_layer.zIndex // Note: This is used for layer toggling.
        });

        // This uses the bounding box instead of the lat/long. See var BuildingPoint function in inventory_map_controller for reference
        const buildingBoundingBox = () => {
          const format = new ol.format.WKT();

          const feature = format.readFeature($scope.bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });

          feature.setProperties($scope.item_state);
          return feature;
        };

        const buildingSources = () => {
          const features = [buildingBoundingBox()];
          return new ol.source.Vector({features: features});
        };

        // Define building UBID bounding box
        const buildingBB = () => {
          const format = new ol.format.WKT();

          const feature = format.readFeature($scope.bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties($scope.item_state);
          return feature;
        };

        // Define building UBID centroid box
        const buildingCentroid = () => {
          const format = new ol.format.WKT();

          const feature = format.readFeature($scope.centroid, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties($scope.item_state);
          return feature;
        };

        const buildingBBSources = () => {
          const features = [buildingBB()];
          return new ol.source.Vector({features: features});
        };

        const buildingCentroidSources = () => {
          const features = [buildingCentroid()];
          return new ol.source.Vector({features: features});
        };

        // Define taxlot UBID bounding box
        const taxlotBB = () => {
          const format = new ol.format.WKT();

          const feature = format.readFeature($scope.bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties($scope.item_state);
          return feature;
        };

        // Define taxlot UBID centroid box
        const taxlotCentroid = () => {
          const format = new ol.format.WKT();

          const feature = format.readFeature($scope.centroid, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties($scope.item_state);
          return feature;
        };

        const taxlotBBSources = () => {
          const features = [taxlotBB()];
          return new ol.source.Vector({features: features});
        };

        const taxlotCentroidSources = () => {
          const features = [taxlotCentroid()];
          return new ol.source.Vector({features: features});
        };

        const clusterSource = () => new ol.source.Cluster({
          source: buildingSources(),
          distance: 45
        });

        // style for building ubid bounding and centroid boxes
        const buildingStyle = (/*feature*/) => new ol.style.Style({
          stroke: new ol.style.Stroke({
            color: '#185189',
            width: 2
          })
        });

        // style for taxlot ubid bounding and centroid boxes
        const taxlotStyle = (/*feature*/) => new ol.style.Style({
          stroke: new ol.style.Stroke({
            color: '#10A0A0',
            width: 2
          })
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

        // Render map
        let layers = [];
        if ($scope.inventory_type === 'properties') {
          layers = [base_layer, $scope.building_bb_layer, $scope.building_centroid_layer];
        } else {
          layers = [base_layer, $scope.taxlot_bb_layer, $scope.taxlot_centroid_layer];
        }
        $scope.map = new ol.Map({
          target: 'map',
          layers: layers
        });


        // Zoom and center based on provided points (none, all, or a subset)
        const zoomCenter = (bounding_box_source, extra_view_options) => {
          if (_.isUndefined(extra_view_options)) extra_view_options = {};
          if (bounding_box_source.isEmpty()) {
            // Default view with no points is the middle of US
            const empty_view = new ol.View({
              center: ol.proj.fromLonLat([-99.066067, 39.390897]),
              zoom: 4.5
            });
            $scope.map.setView(empty_view);
          } else {
            const extent = bounding_box_source.getExtent();

            const view_options = Object.assign({
              size: $scope.map.getSize(),
              padding: [1, 1, 1, 1]
            }, extra_view_options);
            $scope.map.getView().fit(extent, view_options);
          }
        };

        // Set initial zoom and center
        zoomCenter(clusterSource().getSource());


        // map styling
        let element = $scope.map.getViewport().querySelector('.ol-unselectable');
        element.style.border = '1px solid gray';
        element.style.borderRadius = '3px';

        element = $scope.map.getViewport().querySelector('.ol-overlaycontainer-stopevent');
        element.style.display = 'none';
      };

      // Controller Init Function Trigger
      const enableMap = $scope.item_state.ubid && $scope.item_state.bounding_box && $scope.item_state.centroid;
      // Do not map if there is no preferred ubid or it has not been geocoded.
      if (enableMap) {
        init();
      }

    }]);
