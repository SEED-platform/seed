/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
/* eslint-disable no-underscore-dangle */
angular.module('BE.seed.controller.inventory_map', []).controller('inventory_map_controller', [
  '$scope',
  '$stateParams',
  '$state',
  '$log',
  '$uibModal',
  'cycles',
  'inventory_service',
  'map_service',
  'user_service',
  'organization_service',
  'labels',
  'urls',
  // eslint-disable-next-line func-names
  function ($scope, $stateParams, $state, $log, $uibModal, cycles, inventory_service, map_service, user_service, organization_service, labels, urls) {
    $scope.inventory_type = $stateParams.inventory_type;
    const isPropertiesTab = $scope.inventory_type === 'properties';

    $scope.data = [];
    $scope.geocoded_data = [];
    $scope.filteredRecords = 0;
    $scope.highlightDACs = true;

    // find organization's property/taxlot default type to display in popup
    const org_id = user_service.get_organization().id;
    organization_service.get_organization(org_id).then((data) => {
      $scope.default_field = data.organization[isPropertiesTab ? 'property_display_field' : 'taxlot_display_field'];
    });

    const lastCycleId = inventory_service.get_last_cycle();
    $scope.cycle = {
      selected_cycle: _.find(cycles.cycles, { id: lastCycleId }) || _.first(cycles.cycles),
      cycles: cycles.cycles
    };

    $scope.update_cycle = (cycle) => {
      inventory_service.save_last_cycle(cycle.id);
      $state.reload();
    };

    const chunk = 250;
    const fetchRecords = (fn, page = 1) => fn(page, chunk, undefined, undefined).then((data) => {
      $scope.progress = {
        current: data.pagination.end,
        total: data.pagination.total,
        percent: Math.round((data.pagination.end / data.pagination.total) * 100)
      };
      if (data.pagination.has_next) {
        return fetchRecords(fn, page + 1).then((newData) => data.results.concat(newData));
      }
      return data.results;
    });

    $scope.progress = {};
    const loadingModal = $uibModal.open({
      templateUrl: `${urls.static_url}seed/partials/inventory_loading_modal.html`,
      backdrop: 'static',
      windowClass: 'inventory-progress-modal',
      scope: $scope
    });

    const getInventoryFn = isPropertiesTab ? inventory_service.get_properties : inventory_service.get_taxlots;
    fetchRecords(getInventoryFn).then(async (data) => {
      loadingModal.close();

      $scope.data = data;
      $scope.geocoded_data = data.filter(({ long_lat }) => long_lat);
      $scope.filteredRecords = $scope.geocoded_data.length;

      // buildings with UBID bounding boxes and geocoded data
      const geocodedRelated = (data, field) => {
        const related = [];
        for (const record of data) {
          if (record.related) {
            related.push(...record.related.filter((related) => related[field]));
          }
        }
        return _.uniqBy(related, 'id');
      };
      if (isPropertiesTab) {
        $scope.geocoded_properties = $scope.data.filter(({ bounding_box }) => bounding_box);
        $scope.geocoded_taxlots = geocodedRelated($scope.data, 'bounding_box');
      } else {
        $scope.geocoded_properties = geocodedRelated($scope.data, 'bounding_box');
        $scope.geocoded_taxlots = $scope.data.filter(({ bounding_box }) => bounding_box);
      }

      // store a mapping of layers z-index and visibility
      /** @type {Object.<string, {zIndex: number, visible: boolean}>} */
      $scope.layers = {
        base_layer: { zIndex: 0, visible: true },
        census_tract_layer: { zIndex: 1, visible: true },
        hexbin_layer: { zIndex: 2, visible: isPropertiesTab },
        property_bb_layer: { zIndex: 3, visible: isPropertiesTab },
        property_centroid_layer: { zIndex: 4, visible: isPropertiesTab },
        taxlot_bb_layer: { zIndex: 5, visible: !isPropertiesTab },
        taxlot_centroid_layer: { zIndex: 6, visible: !isPropertiesTab },
        points_layer: { zIndex: 7, visible: true }
      };

      const buildingSources = (records) => {
        const features = records.map((record) => {
          const feature = new ol.format.WKT().readFeature(record.long_lat, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
          });
          feature.setProperties(record);
          return feature;
        });

        return new ol.source.Vector({ features });
      };

      const boundingBoxSource = (records) => {
        const features = records.reduce((acc, record) => {
          if (record.bounding_box) {
            try {
              const feature = new ol.format.WKT().readFeature(record.bounding_box, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857'
              });
              feature.setProperties(record);
              acc.push(feature);
            } catch (e) {
              console.error(`Failed to process bounding box for id ${record.id}`);
            }
          }
          return acc;
        }, []);

        return new ol.source.Vector({ features });
      };

      const centroidSource = (records) => {
        const features = records.reduce((acc, record) => {
          if (record.centroid) {
            try {
              const feature = new ol.format.WKT().readFeature(record.centroid, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857'
              });
              feature.setProperties(record);
              acc.push(feature);
            } catch (e) {
              console.error(`Failed to process centroid for id ${record.id}`);
            }
          }
          return acc;
        }, []);

        return new ol.source.Vector({ features });
      };

      const censusTractSource = async () => {
        let geojson = {
          type: 'FeatureCollection',
          features: []
        };

        try {
          // Only show census tracts at a reasonable zoom level
          if ($scope.map?.getView().getZoom() >= 11) {
            const extents = $scope.map.getView().calculateExtent($scope.map.getSize());
            const [west, south, east, north] = ol.proj.transformExtent(extents, $scope.map.getView().getProjection(), 'EPSG:4326');
            const url = `https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/usa_november_2022/FeatureServer/0/query?where=1%3D1&outFields=GEOID10&geometry=${west}%2C${south}%2C${east}%2C${north}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outSR=4326&f=geojson`;
            geojson = await (await fetch(url)).json();
            const tractIds = geojson.features.reduce((acc, { properties: { GEOID10 } }) => acc.concat(GEOID10), []);
            await map_service.checkDisadvantagedStatus(tractIds);
          }
        } catch (e) {
          console.error(e);
        }

        const features = new ol.format.GeoJSON().readFeatures(geojson, {
          featureProjection: 'EPSG:3857'
        });

        return new ol.source.Vector({ features });
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
            stroke: new ol.style.Stroke({ color: '#fff' }),
            fill: new ol.style.Fill({ color: '#3399CC' })
          }),
          text: new ol.style.Text({
            text: size.toString(),
            fill: new ol.style.Fill({ color: '#fff' })
          })
        });
      };

      const singlePointStyle = () => new ol.style.Style({
        image: new ol.style.Icon({
          src: `${urls.static_url}seed/images/map_pin.webp`,
          anchor: [0.5, 1]
        })
      });

      const pointsSource = (records = $scope.geocoded_data) => new ol.source.Cluster({
        source: buildingSources(records),
        distance: 45
      });

      /**
       * style for building ubid bounding and centroid boxes
       * @returns {ol.style.Style}
       */
      const propertyStyle = (/* feature */) => new ol.style.Style({
        stroke: new ol.style.Stroke({
          color: '#185189',
          width: 2
        })
      });

      /**
       * style for taxlot ubid bounding and centroid boxes
       * @returns {ol.style.Style}
       */
      const taxlotStyle = (/* feature */) => new ol.style.Style({
        stroke: new ol.style.Stroke({
          color: '#10A0A0',
          width: 2
        })
      });

      $scope.base_layer = new ol.layer.Tile({
        source: new ol.source.OSM(),
        zIndex: $scope.layers.base_layer.zIndex
      });

      $scope.points_layer = new ol.layer.Vector({
        source: pointsSource(),
        zIndex: $scope.layers.points_layer.zIndex,
        style: (feature) => {
          const size = feature.get('features').length;
          return size > 1 ? clusterPointStyle(size) : singlePointStyle();
        }
      });

      $scope.property_bb_layer = new ol.layer.Vector({
        source: boundingBoxSource($scope.geocoded_properties),
        zIndex: $scope.layers.property_bb_layer.zIndex,
        style: propertyStyle
      });

      $scope.property_centroid_layer = new ol.layer.Vector({
        source: centroidSource($scope.geocoded_properties),
        zIndex: $scope.layers.property_centroid_layer.zIndex,
        style: propertyStyle
      });

      $scope.taxlot_bb_layer = new ol.layer.Vector({
        source: boundingBoxSource($scope.geocoded_taxlots),
        zIndex: $scope.layers.taxlot_bb_layer.zIndex,
        style: taxlotStyle
      });

      $scope.taxlot_centroid_layer = new ol.layer.Vector({
        source: centroidSource($scope.geocoded_taxlots),
        zIndex: $scope.layers.taxlot_centroid_layer.zIndex,
        style: taxlotStyle
      });

      $scope.census_tract_layer = new ol.layer.Vector({
        source: await censusTractSource(),
        zIndex: $scope.layers.census_tract_layer.zIndex,
        style: (feature) => {
          const tractId = feature.values_.GEOID10;
          const isDisadvantaged = map_service.isDisadvantaged(tractId);
          return new ol.style.Style({
            stroke: new ol.style.Stroke({
              color: '#185189',
              width: 2
            }),
            fill: isDisadvantaged && $scope.highlightDACs ? new ol.style.Fill({ color: 'rgba(69, 130, 155, 0.4)' }) : undefined
          });
        }
      });

      // Hexbin layer
      const hexagon_size = 750;

      const hexbinSource = (records = $scope.geocoded_data) => new ol.source.HexBin({
        source: buildingSources(records),
        size: hexagon_size
      });

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

      $scope.hexbin_layer = new ol.layer.Vector({
        source: hexbinSource(),
        zIndex: $scope.layers.hexbin_layer.zIndex,
        opacity: hexbin_max_opacity,
        style: (feature) => {
          const { features } = feature.getProperties();
          const site_eui_key = _.find(_.keys(features[0].values_), (key) => key.startsWith('site_eui'));
          const site_euis = _.map(features, (point) => point.values_[site_eui_key]);
          const total_eui = _.sum(site_euis);
          const opacity = Math.max(hexbin_min_opacity, total_eui / hexagon_size);

          const color = [...$scope.hexbin_color, opacity];
          return [
            new ol.style.Style({
              fill: new ol.style.Fill({ color })
            })
          ];
        }
      });

      // Render map
      const layers = Object.entries($scope.layers).reduce((acc, [layerName, { visible }]) => {
        if (visible) acc.push($scope[layerName]);
        return acc;
      }, []);
      $scope.map = new ol.Map({
        target: 'map',
        layers,
        view: new ol.View({
          maxZoom: 19
        })
      });

      $scope.map.on('moveend', async () => {
        // Re-fetch census tracts
        $scope.census_tract_layer.setSource(await censusTractSource());
      });

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
          const updatedVisibility = visibility ?? !layer.visible;
          $scope.layers[layerName].visible = updatedVisibility;
          if (updatedVisibility) {
            $scope.map.addLayer($scope[layerName]);
          } else {
            $scope.map.removeLayer($scope[layerName]);
          }
        }
      };

      $scope.toggleDACHighlight = () => {
        $scope.highlightDACs = !$scope.highlightDACs;
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
        }
        return `<a href="#/taxlots/${point_info.taxlot_view_id}">${icon_html}</a>`;
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

        $scope.map.forEachFeatureAtPixel(event.pixel, (feature, layer) => {
          // Disregard hexbin/census clicks
          if (![$scope.layers.hexbin_layer.zIndex, $scope.layers.census_tract_layer.zIndex, undefined].includes(layer.getProperties().zIndex)) {
            points.push(...(feature.get('features') ?? []));
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

      const zoomOnCluster = (points) => {
        const source = new ol.source.Vector({ features: points });
        zoomCenter(source, { duration: 750 });
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
          const view_options = {
            size: $scope.map.getSize(),
            padding: [10, 10, 10, 10],
            ...extra_view_options
          };
          $scope.map.getView().fit(extent, view_options);
        }
      };

      // Set initial zoom and center
      zoomCenter(pointsSource().getSource());

      const rerenderPoints = (records) => {
        $scope.filteredRecords = records.length;

        $scope.points_layer.setSource(pointsSource(records));

        if (isPropertiesTab) {
          $scope.hexbin_layer.setSource(hexbinSource(records));
          $scope.property_bb_layer.setSource(boundingBoxSource(records));
          $scope.property_centroid_layer.setSource(centroidSource(records));
        } else {
          $scope.taxlot_bb_layer.setSource(boundingBoxSource(records));
          $scope.taxlot_centroid_layer.setSource(centroidSource(records));
        }
      };

      // Labels
      // Reduce labels to only records found in the current cycle
      $scope.selected_labels = [];

      const updateApplicableLabels = () => {
        /** @type {Set<number>} */
        let inventoryIds;
        if (isPropertiesTab) {
          inventoryIds = new Set($scope.data.map(({ property_view_id }) => property_view_id));
        } else {
          inventoryIds = new Set($scope.data.map(({ taxlot_view_id }) => taxlot_view_id));
        }
        $scope.labels = labels.filter((label) => label.is_applied.some((id) => inventoryIds.has(id)));
        // TODO check this
        // Ensure that no previously-applied labels remain
        const new_labels = $scope.selected_labels.filter((label) => $scope.labels.includes(label.id));
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
        return $scope.labels.filter(({ name }) =>
          // Only include label if its name contains the query string.
          name.toLowerCase().includes(query.toLowerCase()));
      };

      const filterUsingLabels = () => {
        let records = $scope.geocoded_data;
        if (!$scope.selected_labels.length) {
          // Show everything
          return rerenderPoints(records);
        }

        const viewIdProperty = isPropertiesTab ? 'property_view_id' : 'taxlot_view_id';
        if ($scope.labelLogic === 'and') {
          // Find properties/taxlots with all labels
          const viewIds = new Set($scope.selected_labels.map(({ is_applied }) => is_applied).reduce((acc, ids) => acc.filter((id) => ids.includes(id))));
          records = $scope.geocoded_data.filter((record) => viewIds.has(record[viewIdProperty]));
        } else if ($scope.labelLogic === 'or') {
          // Find properties/taxlots with any label
          const viewIds = $scope.selected_labels
            .map(({ is_applied }) => is_applied)
            .reduce((acc, ids) => {
              for (const id of ids) acc.add(id);
              return acc;
            }, new Set());
          records = $scope.geocoded_data.filter((record) => viewIds.has(record[viewIdProperty]));
        } else if ($scope.labelLogic === 'exclude') {
          // Find properties/taxlots with all labels, return everything else
          const viewIds = new Set($scope.selected_labels.map(({ is_applied }) => is_applied).reduce((acc, ids) => acc.filter((id) => ids.includes(id))));
          records = $scope.geocoded_data.filter((record) => !viewIds.has(record[viewIdProperty]));
        }

        inventory_service.saveSelectedLabels(
          localStorageLabelKey,
          $scope.selected_labels.map(({ id }) => id)
        );
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

      // Redraw census tracts on toggle to update styles
      $scope.$watch('highlightDACs', () => $scope.census_tract_layer.changed());

      // Map attribution moved to /about page
      for (const className of ['.ol-attribution', '.ol-rotate']) {
        const element = $scope.map.getViewport().querySelector(className);
        if (element) element.style.display = 'none';
      }
    });
  }
]);
