/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
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
    'user_service',
    'organization_service',
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
      user_service,
      organization_service,
      labels,
      urls
    ) {
      $scope.inventory_type = $stateParams.inventory_type;
      const isPropertiesTab = $scope.inventory_type === 'properties';

      $scope.data = [];
      $scope.geocoded_data = [];
      $scope.filteredRecords = 0;

      // find organization's property/taxlot default type to display in popup
      const org_id = user_service.get_organization().id;
      organization_service.get_organization(org_id).then((data) => {
        $scope.default_field = data.organization[isPropertiesTab ? 'property_display_field' : 'taxlot_display_field'];
      });

      const lastCycleId = inventory_service.get_last_cycle();
      $scope.cycle = {
        selected_cycle: _.find(cycles.cycles, {id: lastCycleId}) || _.first(cycles.cycles),
        cycles: cycles.cycles
      };

      const chunk = 250;
      const fetchRecords = (fn, page = 1) => {
        return fn(page, chunk, undefined, undefined).then((data) => {
          $scope.progress = {
            current: data.pagination.end,
            total: data.pagination.total,
            percent: Math.round(data.pagination.end / data.pagination.total * 100)
          };
          if (data.pagination.has_next) {
            return fetchRecords(fn, page + 1).then((newData) => data.results.concat(newData));
          }
          return data.results;
        });
      };

      $scope.progress = {};
      const loadingModal = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/inventory_loading_modal.html`,
        backdrop: 'static',
        windowClass: 'inventory-progress-modal',
        scope: $scope
      });

      const getInventoryFunc = isPropertiesTab ? inventory_service.get_properties : inventory_service.get_taxlots;

      const getCensusTractGeojson = async () => {
        try {
          // Only show census tracts at a reasonable zoom level
          if ($scope.map?.getView().getZoom() >= 11) {
            const bounds = $scope.map.getView().calculateExtent($scope.map.getSize());
            const [west, south, east, north] = ol.proj.transformExtent(bounds, $scope.map.getView().getProjection(), 'EPSG:4326');
            const url = `https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/usa_november_2022/FeatureServer/0/query?where=1%3D1&outFields=GEOID10&geometry=${west}%2C${south}%2C${east}%2C${north}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outSR=4326&f=geojson`;
            return (await fetch(url)).json();
          }
          return {
            type: 'FeatureCollection',
            features: []
          };
        } catch (e) {
          console.error(e);
        }
      };

      return fetchRecords(getInventoryFunc).then(async (data) => {
        loadingModal.close();

        $scope.data = data;
        $scope.geocoded_data = $scope.data.filter(({long_lat}) => long_lat);
        $scope.filteredRecords = $scope.geocoded_data.length;

        // buildings with UBID bounding boxes and geocoded data
        const geocodedRelated = (data, field) => {
          const related = [];
          for (const record of data) {
            if (record.related) {
              related.push(..._.filter(record.related, field));
            }
          }
          return _.uniqBy(related, 'id');
        };
        if (isPropertiesTab) {
          $scope.geocoded_properties = _.filter($scope.data, 'bounding_box');
          $scope.geocoded_taxlots = geocodedRelated($scope.data, 'bounding_box');
        } else {
          $scope.geocoded_properties = geocodedRelated($scope.data, 'bounding_box');
          $scope.geocoded_taxlots = _.filter($scope.data, 'bounding_box');
        }

        // store a mapping of layers z-index and visibility
        /** @type {Object.<string, {zIndex: number, visible: boolean}>} */
        $scope.layers = {
          base_layer: {zIndex: 0, visible: true},
          hexbin_layer: {zIndex: 1, visible: isPropertiesTab},
          points_layer: {zIndex: 2, visible: true},
          building_bb_layer: {zIndex: 3, visible: isPropertiesTab},
          building_centroid_layer: {zIndex: 4, visible: isPropertiesTab},
          taxlot_bb_layer: {zIndex: 5, visible: !isPropertiesTab},
          taxlot_centroid_layer: {zIndex: 6, visible: !isPropertiesTab},
          census_tract_layer: {zIndex: 7, visible: true}
        };

        // Map
        const base_layer = new ol.layer.Tile({
          source: new ol.source.OSM(),
          zIndex: $scope.layers.base_layer.zIndex // Note: This is used for layer toggling.
        });

        // Define buildings source - the basis of layers
        const buildingPoint = (building) => {
          const format = new ol.format.WKT();

          const feature = format.readFeature(building.long_lat, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });

          feature.setProperties(building);
          return feature;
        };

        const buildingSources = (records = $scope.geocoded_data) => {
          const features = _.map(records, buildingPoint);

          return new ol.source.Vector({features});
        };

        // Define building UBID bounding box
        const buildingBB = (building) => {
          if (building.bounding_box) {
            try {
              const format = new ol.format.WKT();

              const feature = format.readFeature(building.bounding_box, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857'
              });
              feature.setProperties(building);
              return feature;
            } catch (e) {
              console.error(`Failed to process bounding box for id ${building.id}`);
            }
          }
        };

        // Define building UBID centroid box
        const buildingCentroid = (building) => {
          const format = new ol.format.WKT();

          const feature = format.readFeature(building.centroid, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(building);
          return feature;
        };

        const buildingBBSources = (records = $scope.geocoded_properties) => {
          console.log('buildingBBSources');
          const features = records.reduce((acc, record) => {
            const result = buildingBB(record);
            if (result) acc.push(result);
            return acc;
          }, []);

          return new ol.source.Vector({features});
        };

        const buildingCentroidSources = (records = $scope.geocoded_properties) => {
          const features = _.map(records, buildingCentroid);

          return new ol.source.Vector({features: features});
        };

        /**
         * Define taxlot UBID bounding box
         * @param taxlot
         * @returns {*}
         */
        const taxlotBB = (taxlot) => {
          const format = new ol.format.WKT();

          const feature = format.readFeature(taxlot.bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(taxlot);
          return feature;
        };

        /**
         * Define taxlot UBID centroid box
         * @param taxlot
         * @returns {*}
         */
        const taxlotCentroid = (taxlot) => {
          const format = new ol.format.WKT();

          const feature = format.readFeature(taxlot.centroid, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(taxlot);
          return feature;
        };

        const taxlotBBSources = (records = $scope.geocoded_taxlots) => {
          const features = _.map(records, taxlotBB);

          return new ol.source.Vector({features: features});
        };

        const taxlotCentroidSources = (records = $scope.geocoded_taxlots) => {
          const features = _.map(records, taxlotCentroid);

          return new ol.source.Vector({features: features});
        };

        /**
         * Points/clusters layer
         * @param {number} size
         * @returns {ol.style.Style}
         */
        const clusterPointStyle = (size) => {
          const relative_radius = 10 + Math.min(7, size / 50);
          return new ol.style.Style({
            image: new ol.style.Circle({
              radius: relative_radius,
              stroke: new ol.style.Stroke({color: '#fff'}),
              fill: new ol.style.Fill({color: '#3399CC'})
            }),
            text: new ol.style.Text({
              text: size.toString(),
              fill: new ol.style.Fill({color: '#fff'})
            })
          });
        };

        const singlePointStyle = () => new ol.style.Style({
          image: new ol.style.Icon({
            src: `${urls.static_url}seed/images/map_pin.png`,
            scale: 0.05,
            anchor: [0.5, 1]
          })
        });

        const clusterSource = (records = $scope.geocoded_data) => new ol.source.Cluster({
          source: buildingSources(records),
          distance: 45
        });

        const pointsLayerStyle = (feature) => {
          const size = feature.get('features').length;
          return size > 1 ? clusterPointStyle(size) : singlePointStyle();
        };

        /**
         * style for building ubid bounding and centroid boxes
         * @returns {ol.style.Style}
         */
        const buildingStyle = (/*feature*/) => new ol.style.Style({
          stroke: new ol.style.Stroke({
            color: '#185189',
            width: 2
          })
        });

        /**
         * style for taxlot ubid bounding and centroid boxes
         * @returns {ol.style.Style}
         */
        const taxlotStyle = (/*feature*/) => new ol.style.Style({
          stroke: new ol.style.Stroke({
            color: '#10A0A0',
            width: 2
          })
        });

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

        const geojson = await getCensusTractGeojson();
        console.log('geojson', geojson);
        $scope.census_tract_layer = new ol.layer.Vector({
          source: new ol.source.Vector({
            features: (new ol.format.GeoJSON()).readFeatures(geojson, {featureProjection: 'EPSG:3857'})
          })
        });

        // Hexbin layer
        const hexagon_size = 750;

        const hexbinSource = (records = $scope.geocoded_data) => {
          return new ol.source.HexBin({
            source: buildingSources(records),
            size: hexagon_size
          });
        };

        $scope.hexbin_color = [75, 0, 130];
        const hexbin_max_opacity = 0.8;
        const hexbin_min_opacity = 0.2;

        $scope.hexbinInfoBarColor = () => {
          const hexbin_color_code = $scope.hexbin_color.join(',');
          const left_color = `rgb(${hexbin_color_code},${hexbin_max_opacity * hexbin_min_opacity})`;
          const right_color = `rgb(${hexbin_color_code},${hexbin_max_opacity})`;

          return {
            background: `linear-gradient(to right, ${left_color}, ${right_color})`
          };
        };

        /**
         * @param {number} opacity
         * @returns {[ol.style.Style]}
         */
        const hexagonStyle = (opacity) => {
          const color = [...$scope.hexbin_color, opacity];
          return [
            new ol.style.Style({
              fill: new ol.style.Fill({color})
            })
          ];
        };

        const hexbinStyle = (feature) => {
          const {features} = feature.getProperties();
          const site_eui_key = _.find(_.keys(features[0].values_), (key) => key.startsWith('site_eui'));
          const site_euis = _.map(features, (point) => point.values_[site_eui_key]);
          const total_eui = _.sum(site_euis);
          const opacity = Math.max(hexbin_min_opacity, total_eui / hexagon_size);

          return hexagonStyle(opacity);
        };

        $scope.hexbin_layer = new ol.layer.Vector({
          source: hexbinSource(),
          zIndex: $scope.layers.hexbin_layer.zIndex, // Note: This is used for layer toggling.
          opacity: hexbin_max_opacity,
          style: hexbinStyle
        });

        // Render map
        const layers = [];
        if (isPropertiesTab) {
          layers.push(...[base_layer, $scope.hexbin_layer, $scope.points_layer, $scope.building_bb_layer, $scope.building_centroid_layer, $scope.census_tract_layer]);
        } else {
          layers.push(...[base_layer, $scope.points_layer, $scope.taxlot_bb_layer, $scope.taxlot_centroid_layer, $scope.census_tract_layer]);
        }
        $scope.map = new ol.Map({
          target: 'map',
          layers: layers,
          view: new ol.View({
            maxZoom: 19
          })
        });

        $scope.map.on('moveend', async (e) => {
          const geojson = await getCensusTractGeojson();
          console.log('MOVE END', geojson);
          $scope.census_tract_layer.setSource(new ol.source.Vector({
            features: (new ol.format.GeoJSON()).readFeatures(geojson, {featureProjection: 'EPSG:3857'})
          }));
        });

        // Toggle layers

        // If a layer's z-index is changed, it should be changed here as well.
        const layer_at_z_index = {
          0: base_layer,
          1: $scope.hexbin_layer,
          2: $scope.points_layer,
          3: $scope.building_bb_layer,
          4: $scope.building_centroid_layer,
          5: $scope.taxlot_bb_layer,
          6: $scope.taxlot_centroid_layer,
          7: $scope.census_tract_layer
        };

        /**
         * @param {number} zIndex
         * @returns {boolean}
         */
        $scope.layerVisible = (zIndex) => {
          const layers = $scope.map.getLayers().array_;
          return layers.some((layer) => layer.values_.zIndex === zIndex);
        };

        /**
         * @param {string} layerName
         * @param {boolean} [visibility]
         */
        $scope.toggleLayer = (layerName, visibility) => {
          const layer = $scope.layers[layerName];
          if (layer) {
            const {visible, zIndex} = layer;
            const updatedVisibility = visibility ?? !visible;
            $scope.layers[layerName].visible = updatedVisibility;
            if (updatedVisibility) {
              $scope.map.addLayer(layer_at_z_index[zIndex]);
            } else {
              $scope.map.removeLayer(layer_at_z_index[zIndex]);
            }
          }
        };

        // Define overlay attaching html element
        const popupOverlay = new ol.Overlay({
          element: document.getElementById('popup-element'),
          positioning: 'bottom-center',
          stopEvent: false,
          autoPan: true,
          autoPanMargin: 75,
          offset: [0, -135]
        });
        $scope.map.addOverlay(popupOverlay);

        /**
         * @param {({property_view_id: number}|{taxlot_view_id: number})} point_info
         * @returns {string}
         */
        const detailPageIcon = (point_info) => {
          const icon_html = '<i class="ui-grid-icon-info-circled"></i>';

          if (isPropertiesTab) {
            return `<a href="#/properties/${point_info.property_view_id}">${icon_html}</a>`;
          } else {
            return `<a href="#/taxlots/${point_info.taxlot_view_id}">${icon_html}</a>`;
          }
        };

        const showPointInfo = (point, element) => {
          const pop_info = point.getProperties();
          const default_display_key = _.find(_.keys(pop_info), (key) => key.startsWith($scope.default_field));

          const coordinates = point.getGeometry().getCoordinates();

          popupOverlay.setPosition(coordinates);
          $(element).popover({
            placement: 'top',
            html: true,
            selector: true,
            content: pop_info[default_display_key] + detailPageIcon(pop_info)
          });

          $(element).popover('show');
        };

        $scope.map.on('click', (event) => {
          const element = popupOverlay.getElement();
          const points = [];
          console.log('CLICKED');

          $scope.map.forEachFeatureAtPixel(event.pixel, (feature, layer) => {
            // Disregard hexbin/census clicks
            console.log('Feature', feature);
            console.log('Layer', layer);
            if (![$scope.layers.hexbin_layer.zIndex, $scope.layers.census_tract_layer.zIndex, undefined].includes(layer.getProperties().zIndex)) {
              points.push(...feature.get('features'));
            }
          });

          if (!points.length) {
            $(element).popover('destroy');
          } else if (points.length === 1) {
            showPointInfo(points[0], element);
          } else {
            zoomOnCluster(points);
          }
        });

        const zoomOnCluster = points => {
          const source = new ol.source.Vector({features: points});
          zoomCenter(source, {duration: 750});
        };

        // Zoom and center based on provided points (none, all, or a subset)
        const zoomCenter = (points_source, extra_view_options = {}) => {
          if (points_source.isEmpty()) {
            // Default view with no points is the middle of US
            const empty_view = new ol.View({
              center: ol.proj.fromLonLat([-99.066067, 39.390897]),
              zoom: 4.5
            });
            $scope.map.setView(empty_view);
          } else {
            const extent = points_source.getExtent();
            const view_options = Object.assign({
              size: $scope.map.getSize(),
              padding: [10, 10, 10, 10]
            }, extra_view_options);
            $scope.map.getView().fit(extent, view_options);
          }
        };

        // Set initial zoom and center
        zoomCenter(clusterSource().getSource());

        const rerenderPoints = (records) => {
          $scope.filteredRecords = records.length;

          $scope.points_layer.setSource(clusterSource(records));

          if (isPropertiesTab) {
            $scope.hexbin_layer.setSource(hexbinSource(records));
            $scope.building_bb_layer.setSource(buildingBBSources(records));
          } else {

          }
        };

        // Labels
        // Reduce labels to only records found in the current cycle
        $scope.selected_labels = [];

        const updateApplicableLabels = () => {
          /** @type {Set<number>} */
          let inventoryIds;
          if (isPropertiesTab) {
            inventoryIds = new Set($scope.data.map(({property_view_id}) => property_view_id));
          } else {
            inventoryIds = new Set($scope.data.map(({taxlot_view_id}) => taxlot_view_id));
          }
          $scope.labels = labels.filter((label) => {
            return label.is_applied.some((id) => inventoryIds.has(id));
          });
          // TODO check this
          // Ensure that no previously-applied labels remain
          const new_labels = $scope.selected_labels.filter((label) => {
            return $scope.labels.includes(label.id);
          });
          if ($scope.selected_labels.length !== new_labels.length) {
            $scope.selected_labels = new_labels;
          }
        };

        updateApplicableLabels();

        const localStorageLabelKey = `grid.${$scope.inventory_type}.labels`;

        // Reapply valid previously-applied labels
        const ids = inventory_service.loadSelectedLabels(localStorageLabelKey);
        $scope.selected_labels = $scope.labels.filter((label) => ids.includes(label.id));

        $scope.clearLabels = () => {
          $scope.selected_labels = [];
        };

        /**
         * Filter list of labels while typing
         * @param {string} query
         * @returns {Label[]}
         */
        $scope.loadLabelsForFilter = (query) => {
          if (!query.trim()) return $scope.labels;
          return $scope.labels.filter(({name}) => {
            // Only include label if its name contains the query string.
            return name.toLowerCase().includes(query.toLowerCase());
          });
        };

        const filterUsingLabels = () => {
          let records = $scope.geocoded_data;
          if (!$scope.selected_labels.length) {
            // Show everything
            return rerenderPoints(records);
          }

          if ($scope.labelLogic === 'and') {
            // Find properties/taxlots with all labels
            const ids = new Set($scope.selected_labels.map(({is_applied}) => is_applied).reduce((acc, ids) => acc.filter(id => ids.includes(id))));
            records = $scope.geocoded_data.filter(({id}) => ids.has(id));
          } else if ($scope.labelLogic === 'or') {
            // Find properties/taxlots with any label
            const ids = $scope.selected_labels.map(({is_applied}) => is_applied).reduce((acc, ids) => {
              for (const id of ids) acc.add(id);
              return acc;
            }, new Set());
            records = $scope.geocoded_data.filter(({id}) => ids.has(id));
          } else if ($scope.labelLogic === 'exclude') {
            // Find properties/taxlots with all labels, return everything else
            const ids = new Set($scope.selected_labels.map(({is_applied}) => is_applied).reduce((acc, ids) => acc.filter(id => ids.includes(id))));
            records = $scope.geocoded_data.filter(({id}) => !ids.has(id));
          }

          inventory_service.saveSelectedLabels(localStorageLabelKey, $scope.selected_labels.map(({id}) => id));
          rerenderPoints(records);
        };

        $scope.labelLogic = localStorage.getItem('labelLogic');
        $scope.labelLogic = ['and', 'or', 'exclude'].includes($scope.labelLogic) ? $scope.labelLogic : 'and';
        $scope.labelLogicUpdated = (labelLogic) => {
          $scope.labelLogic = labelLogic;
          localStorage.setItem('labelLogic', $scope.labelLogic);
          filterUsingLabels();
        };

        $scope.$watchCollection('selected_labels', filterUsingLabels);

        const refreshUsingCycle = () => {
          if (isPropertiesTab) {
            $scope.data = inventory_service.get_properties(1, undefined, $scope.cycle.selected_cycle, undefined).results;
            $state.reload();
          } else {
            $scope.data = inventory_service.get_taxlots(1, undefined, $scope.cycle.selected_cycle, undefined).results;
            $state.reload();
          }
        };

        $scope.update_cycle = (cycle) => {
          inventory_service.save_last_cycle(cycle.id);
          $scope.cycle.selected_cycle = cycle;
          refreshUsingCycle();
        };

        // Map attribution moved to /about page
        for (const className of ['.ol-attribution', '.ol-rotate']) {
          const element = $scope.map.getViewport().querySelector(className);
          if (element) element.style.display = 'none';
        }
      });
    }]);
