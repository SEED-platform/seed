/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.inventory_detail_map', [])
    .controller('inventory_detail_map_controller', [
        '$scope',
        '$stateParams',
        '$state',
        '$uibModal',
        'inventory_service',
        'user_service',
        'organization_service',
        'urls',
        function (
            $scope,
            $stateParams,
            $state,
            $uibModal,
            inventory_service,
            user_service,
            organization_service,
            urls,
        ) {
            labels = $scope.labels;
            cycles = $scope.cycles;
            $scope.inventory_type = $stateParams.inventory_type;

            $scope.bounding_box = $scope.item_state.bounding_box.replace(/^SRID=\d+;/, '');
            $scope.centroid = $scope.item_state.centroid.replace(/^SRID=\d+;/, '');

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
                    // $scope.progress = {
                    //     current: data.pagination.end,
                    //     total: data.pagination.total,
                    //     percent: Math.round(data.pagination.end / data.pagination.total * 100)
                    // };
                    if (data.pagination.has_next) {
                        return fetch(page + 1, chunk).then(function (data2) {
                            return data.results.concat(data2);
                        });
                    }
                    return data.results;
                });
            };

            var page = 1;
            var chunk = 1;
            var include_view_ids = [$stateParams.view_id]
            // $scope.progress = {};
            // var modalInstance = $uibModal.open({
            //     templateUrl: urls.static_url + 'seed/partials/inventory_loading_modal.html',
            //     backdrop: 'static',
            //     windowClass: 'inventory-progress-modal',
            //     scope: $scope
            // });


            $scope.$watch('reload', () => {
                $scope.reload && $state.reload()
            })

            var getInventoryFunc;
            if ($scope.inventory_type == 'properties') getInventoryFunc = inventory_service.get_properties;
            else getInventoryFunc = inventory_service.get_taxlots;
            return fetch(page, chunk, include_view_ids, getInventoryFunc).then(function (data) {
                // modalInstance.close();

                // Do not map if there is no preferred ubid.
                if (!$scope.item_state.ubid) {
                    return
                }

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

                // This uses the bounding box instead of the lat/long. See var BuildingPoint function in inventory_map_controller for reference
                var buildingBoundingBox = function (building) {
                    var format = new ol.format.WKT();

                    var feature = format.readFeature($scope.bounding_box, {
                    // var feature = format.readFeature(building.bounding_box, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });

                    feature.setProperties(building);
                    return feature;
                }

                var buildingSources = function (records) {
                    if (_.isUndefined(records)) records = $scope.geocoded_data;
                    var features = _.map(records, buildingBoundingBox);
                    // var features = _.map(records, buildingPoint);

                    return new ol.source.Vector({ features: features });
                };

                // Define building UBID bounding box
                var buildingBB = function (building) {
                    var format = new ol.format.WKT();

                    // var feature = format.readFeature(building.bounding_box, {
                    var feature = format.readFeature($scope.bounding_box, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });
                    feature.setProperties(building);
                    return feature;
                };

                // Define building UBID centroid box
                var buildingCentroid = function (building) {
                    var format = new ol.format.WKT();

                    var feature = format.readFeature($scope.centroid, {
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

                    var feature = format.readFeature($scope.bounding_box, {
                        dataProjection: 'EPSG:4326',
                        featureProjection: 'EPSG:3857'
                    });
                    feature.setProperties(taxlot);
                    return feature;
                };

                // Define taxlot UBID centroid box
                var taxlotCentroid = function (taxlot) {
                    var format = new ol.format.WKT();

                    var feature = format.readFeature($scope.centroid, {
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

                var clusterSource = function (records) {
                    if (_.isUndefined(records)) records = $scope.geocoded_data;
                    return new ol.source.Cluster({
                        source: buildingSources(records),
                        distance: 45
                    });
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
                    layers = [base_layer, $scope.building_bb_layer, $scope.building_centroid_layer];
                } else {
                    layers = [base_layer, $scope.points_layer, $scope.taxlot_bb_layer, $scope.taxlot_centroid_layer];
                }
                $scope.map = new ol.Map({
                    target: 'map',
                    layers: layers
                });


                // Zoom and center based on provided points (none, all, or a subset)
                var zoomCenter = function (bounding_box_source, extra_view_options) {
                    if (_.isUndefined(extra_view_options)) extra_view_options = {};
                    if (bounding_box_source.isEmpty()) {
                        // Default view with no points is the middle of US
                        var empty_view = new ol.View({
                            center: ol.proj.fromLonLat([-99.066067, 39.390897]),
                            zoom: 4.5
                        });
                        $scope.map.setView(empty_view);
                    } else {
                        var extent = bounding_box_source.getExtent();

                        var view_options = Object.assign({
                            size: $scope.map.getSize(),
                            padding: [1, 1, 1, 1],
                        }, extra_view_options);
                        $scope.map.getView().fit(extent, view_options);
                    }
                };

                // Set initial zoom and center
                zoomCenter(clusterSource().getSource());


                // map styling
                let element = $scope.map.getViewport().querySelector('.ol-unselectable');
                element.style.border = '1px solid gray';
                element.style.borderRadius = '3px'

                element = $scope.map.getViewport().querySelector('.ol-overlaycontainer-stopevent')
                element.style.display = 'none';

            });
        }]);
