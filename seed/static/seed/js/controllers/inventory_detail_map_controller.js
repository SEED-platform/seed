/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_map', [])
    .controller('inventory_detail_map_controller', [
        '$scope',
        '$stateParams',
        '$state',
        '$log',
        '$uibModal',
        'inventory_service',
        'user_service',
        'organization_service',
        'urls',
        function (
            $scope,
            $stateParams,
            $state,
            $log,
            $uibModal,
            inventory_service,
            user_service,
            organization_service,
            urls,
        ) {
            $scope.test = 'abcd'
            labels = $scope.labels;
            cycles = $scope.cycles;
            $scope.inventory_type = $stateParams.inventory_type;

            $scope.data = [];
            $scope.geocoded_data = [];
            $scope.ungeocoded_data = [];

            // find organization's property/taxlot default type to display in popup
            const org_id = user_service.get_organization().id;
            organization_service.get_organization(org_id).then(function (data) {
                if ($scope.inventory_type == 'properties') {
                    $scope.default_field = data.organization.property_display_field;
                } else {
                    $scope.default_field = data.organization.taxlot_display_field;
                }
            });

            var lastCycleId = inventory_service.get_last_cycle();
            $scope.cycle = {
                selected_cycle: _.find(cycles.cycles, { id: lastCycleId }) || _.first(cycles.cycles),
                cycles: cycles.cycles
            };
            var fetch = function (page, chunk, include_view_ids, func) {
                return func(page, chunk, undefined, undefined, include_view_ids).then(function (data) {
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
            var include_view_ids = [$stateParams.view_id]
            $scope.progress = {};
            var modalInstance = $uibModal.open({
                templateUrl: urls.static_url + 'seed/partials/inventory_loading_modal.html',
                backdrop: 'static',
                windowClass: 'inventory-progress-modal',
                scope: $scope
            });



            var getInventoryFunc;
            if ($scope.inventory_type == 'properties') getInventoryFunc = inventory_service.get_properties;
            else getInventoryFunc = inventory_service.get_taxlots;
            return fetch(page, chunk, include_view_ids, getInventoryFunc).then(function (data) {
                modalInstance.close();

                $scope.data = data;
                $scope.geocoded_data = _.filter($scope.data, 'long_lat');
                $scope.ungeocoded_data = _.reject($scope.data, 'long_lat');

                // buildings with UBID bounding boxes and geocoded data
                var geocodedRelated = function (data, field) {
                    var related = [];
                    _.each(data, function (record) {
                        if (!_.isUndefined(record.related) && !_.isEmpty(record.related)) {
                            related = _.concat(related, _.filter(record.related, field));
                        }
                    });
                    return _.uniqBy(related, 'id');
                };
                if ($scope.inventory_type === 'properties') {
                    $scope.geocoded_properties = _.filter($scope.data, 'bounding_box');
                    $scope.geocoded_taxlots = geocodedRelated($scope.data, 'bounding_box');
                } else {
                    $scope.geocoded_properties = geocodedRelated($scope.data, 'bounding_box');
                    $scope.geocoded_taxlots = _.filter($scope.data, 'bounding_box');
                }

                // store a mapping of layers z-index and visibility
                $scope.layers = {};
                $scope.layers.base_layer = { zIndex: 0, visible: 1 };
                if ($scope.inventory_type === 'properties') {
                    $scope.layers.points_layer = { zIndex: 2, visible: 1 };
                    $scope.layers.building_bb_layer = { zIndex: 3, visible: 1 };
                    $scope.layers.building_centroid_layer = { zIndex: 4, visible: 1 };
                    $scope.layers.taxlot_bb_layer = { zIndex: 5, visible: 0 };
                    $scope.layers.taxlot_centroid_layer = { zIndex: 6, visible: 0 };
                } else {
                    // taxlots
                    $scope.layers.points_layer = { zIndex: 2, visible: 1 };
                    $scope.layers.building_bb_layer = { zIndex: 3, visible: 0 };
                    $scope.layers.building_centroid_layer = { zIndex: 4, visible: 0 };
                    $scope.layers.taxlot_bb_layer = { zIndex: 5, visible: 1 };
                    $scope.layers.taxlot_centroid_layer = { zIndex: 6, visible: 1 };
                }

                // Map
                var base_layer = new ol.layer.Tile({
                    source: new ol.source.Stamen({
                        layer: 'terrain'
                    }),
                    zIndex: $scope.layers.base_layer.zIndex // Note: This is used for layer toggling.
                });

                // Define buildings source - the basis of layers
                var buildingPoint = function (building) {
                    console.log('buildingPoint')
                    var format = new ol.format.WKT();

                    var feature = format.readFeature(building.long_lat, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });

                    feature.setProperties(building);
                    return feature;
                };

                var buildingBoundingBox = function (building) {
                    console.log('buildingBoundingBox')
                    var format = new ol.format.WKT();

                    var feature = format.readFeature(building.bounding_box, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });

                    feature.setProperties(building);
                    return feature;
                }

                var buildingSources = function (records) {
                    console.log('buildingSources')
                    if (_.isUndefined(records)) records = $scope.geocoded_data;
                    var features = _.map(records, buildingBoundingBox);
                    // var features = _.map(records, buildingPoint);

                    return new ol.source.Vector({ features: features });
                };

                // Define building UBID bounding box
                var buildingBB = function (building) {
                    var format = new ol.format.WKT();

                    var feature = format.readFeature(building.bounding_box, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });
                    feature.setProperties(building);
                    return feature;
                };

                // Define building UBID centroid box
                var buildingCentroid = function (building) {
                    var format = new ol.format.WKT();

                    var feature = format.readFeature(building.centroid, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });
                    feature.setProperties(building);
                    return feature;
                };

                var buildingBBSources = function (records) {
                    if (_.isUndefined(records)) records = $scope.geocoded_properties;
                    var features = _.map(records, buildingBB);

                    return new ol.source.Vector({ features: features });
                };

                var buildingCentroidSources = function (records) {
                    if (_.isUndefined(records)) records = $scope.geocoded_properties;
                    var features = _.map(records, buildingCentroid);

                    return new ol.source.Vector({ features: features });
                };

                // Define taxlot UBID bounding box
                var taxlotBB = function (taxlot) {
                    var format = new ol.format.WKT();

                    var feature = format.readFeature(taxlot.bounding_box, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });
                    feature.setProperties(taxlot);
                    return feature;
                };

                // Define taxlot UBID centroid box
                var taxlotCentroid = function (taxlot) {
                    var format = new ol.format.WKT();

                    var feature = format.readFeature(taxlot.centroid, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });
                    feature.setProperties(taxlot);
                    return feature;
                };

                var taxlotBBSources = function (records) {
                    if (_.isUndefined(records)) records = $scope.geocoded_taxlots;
                    var features = _.map(records, taxlotBB);

                    return new ol.source.Vector({ features: features });
                };

                var taxlotCentroidSources = function (records) {
                    if (_.isUndefined(records)) records = $scope.geocoded_taxlots;
                    var features = _.map(records, taxlotCentroid);

                    return new ol.source.Vector({ features: features });
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
                            fill: new ol.style.Fill({ color: '#fff' })
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
                    console.log('clusterSource')
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

                // style for taxlot ubid bounding and centroid boxes
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

                // Render map
                var layers = [];
                if ($scope.inventory_type === 'properties') {
                    // layers = [base_layer, $scope.hexbin_layer, $scope.points_layer, $scope.building_bb_layer, $scope.building_centroid_layer];
                    layers = [base_layer, $scope.points_layer, $scope.building_bb_layer, $scope.building_centroid_layer];
                } else {
                    layers = [base_layer, $scope.points_layer, $scope.taxlot_bb_layer, $scope.taxlot_centroid_layer];
                }
                $scope.map = new ol.Map({
                    target: 'map',
                    layers: layers
                });

                // Toggle layers

                // If a layer's z-index is changed, it should be changed here as well.
                var layer_at_z_index = {
                    0: base_layer,
                    // 1: $scope.hexbin_layer,
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
                            point_info.taxlot_view_id +
                            '">' +
                            icon_html +
                            '</a>';
                    }

                    return link_html;
                };

                var showPointInfo = function (point) {
                    var pop_info = point.getProperties();
                    var default_display_key = _.find(_.keys(pop_info), function (key) {
                        return _.startsWith(key, $scope.default_field);
                    });

                    var coordinates = point.getGeometry().getCoordinates();

                    popup_overlay.setPosition(coordinates);
                    $(popup_element).popover({
                        placement: 'top',
                        html: true,
                        selector: true,
                        content: pop_info[default_display_key] + detailPageIcon(pop_info)
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
                    console.log('zoomOnCluster')
                    var source = new ol.source.Vector({ features: points });
                    zoomCenter(source, { duration: 750 });
                };

                // Zoom and center based on provided points (none, all, or a subset)
                var zoomCenter = function (points_source, extra_view_options) {
                    console.log('zoomCenter')
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
                        // var feature = format.readFeature(wktString, {
                        //     dataProjection: 'EPSG:4326',
                        //     featureProjection: 'EPSG:3857'
                        // });

                        // var extent = feature.getExtent()
                        // this extent is in lat long coords
                        console.log('extent', extent)

                        var view_options = Object.assign({
                            size: $scope.map.getSize(),
                            padding: [1, 1, 1, 1],
                        }, extra_view_options);
                        $scope.map.getView().fit(extent, view_options);
                    }
                    console.log('current zoom', $scope.map.getView().getZoom())
                };

                // Set initial zoom and center
                console.log('initial zoom')
                zoomCenter(clusterSource().getSource());

                var rerenderPoints = function (records) {
                    $scope.points_layer.setSource(clusterSource(records));
                    // $scope.hexbin_layer.setSource(hexbinSource(records));
                };

                // Labels
                // Reduce labels to only records found in the current cycle
                $scope.selected_labels = [];

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

                var canvasElement = $scope.map.getViewport().querySelector('.ol-unselectable');

                canvasElement.style.width = '50%';
                canvasElement.style.margin = 'auto';
                canvasElement.style.border = '2px solid gray';

                $scope.$watch('reload', () => {
                    console.log('watch reload')
                    $scope.reload &&$state.reload()
                })
            

                
            });
        }]);
