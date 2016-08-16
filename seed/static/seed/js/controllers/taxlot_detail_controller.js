/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.taxlot_detail_controller', [])
.controller('taxlot_detail_controller', [
  '$scope',
  '$routeParams',
  '$uibModal',
  '$log',
  'property_taxlot_service',
  'property_payload',
  'all_columns',
  'urls',
  '$filter',
  '$location',
  'label_helper_service',
  'default_columns',
  function($scope, $routeParams, $uibModal, $log, properties_taxlots_service, property_payload, all_columns, urls, $filter, $location, label_helper_service, default_columns) {
    $scope.user = {};
    $scope.user.taxlot_id = $routeParams.taxlot_id;
    $scope.taxlot = taxlot_payload.taxlot;
    $scope.user_role = property_payload.user_role;
    $scope.user_org_id = property_payload.user_org_id;

    $scope.fields = all_columns.fields;
    $scope.default_columns = default_columns.columns;

		// Holds a copy of original state of property. Used
		// when 'Cancel' is selected and property should be
		// returned to original state.
		$scope.taxlot_copy = {};

    $scope.data_fields = [];

    // set the tab
    $scope.section = $location.hash();
    $scope.status = {
        isopen: false
    };

    var get_labels = function(property) {
        return _.map(property.labels, function(lbl) {
          lbl.label = label_helper_service.lookup_label(lbl.color);
          return lbl;
        });
    };

    $scope.labels = get_labels(property_payload);

    /**
     * save_property_state: saves the property state in case cancel gets clicked
     */
    $scope.save_property_state = function () {
        $scope.property_copy = angular.copy($scope.property);
    };

    /**
     * restore_property: restores the property from its copy
     *   and hides the edit fields
     */
    $scope.restore_property = function () {
        $scope.property = $scope.property_copy;
        $scope.property.edit_form_showing = false;
    };


    /**
     * save_taxlot: saves the Tax Lot's updates
     */
    $scope.save_taxlot = function (){
        $scope.$emit('show_saving');
        property_taxlot_service.update_taxlot($scope.taxlot, $scope.user_org_id)
        .then(function (data){
            $scope.$emit('finished_saving');
        }, function (data, status){
            // reject promise
            $scope.$emit('finished_saving');
        }).catch(function (data) {
            console.log( String(data) );
        });
    };


    /**
     * is_valid_key: checks to see if the key or attribute should be excluded
     *   from data columns
		 *
		 *   DMCQ TODO: Update to columns appropriate for BLUESKY
		 *   I'm assuming most of these are for older snapshot data model
		 *
     */
    $scope.is_valid_data_column_key = function (key) {
        var known_invalid_keys = [
            'best_guess_confidence',
            'best_guess_canonical_building',
            'canonical_building',
            'canonical_for_ds',
            'children',
            'confidence',
            'created',
            'extra_data',
            'extra_data_sources',
            'id',
            'is_master',
            'import_file',
            'import_file_name',
            'last_modified_by',
            'match_type',
            'modified',
            'model',
            'parents',
            'pk',
            'super_organization',
            'source_type',
            'duplicate',
            'co_parent'
        ];
        var no_invalid_key = !_.includes(known_invalid_keys, key);

        return (!_.includes(key, '_source') && !_.includes(key, 'extra_data') && !_.includes(key, '$$') && no_invalid_key);
    };


    /**
     * generate_data_fields: returns a list of objects representing
		 * the data fields (fixed column and extra_data) to show for
		 * the given 'taxlot.'
		 * This method makes sure keys/fields are not duplicated.
		 * Also, this method only adds columns that are in the
		 * default_columns property for the current user (if any exist).
     *
     * @returns {Array} data_fields: list of data_field objects
		 *
     */
    $scope.generate_data_fields = function(taxlot) {
        var data_fields = [];
        var key_list = [];
        var check_defaults = !!$scope.default_columns.length;


        // add fixed_column property properties to data_fields
        angular.forEach(taxlot, function ( val, key ) {
            // Duplicate check and check if default_columns is used and if field in columns
            if ( $scope.is_valid_key(key) && !_.isUndefined(val) && !_.includes(key_list, key) &&
                (!check_defaults || (check_defaults && _.includes($scope.default_columns, key)))) {
                key_list.push(key);
                data_fields.push({
                    key: key,
                    type: 'fixed_column'
                });
            }
        });

        // add extra_data properties for property to data_fields
				angular.forEach(property.extra_data, function (val, key){
						// Duplicate check and check if default_columns is used and if field in columns
						if ($scope.is_valid_key(key) && !_.includes(key_list, key) &&
								(!check_defaults || (check_defaults && _.includes($scope.default_columns, key)))) {
								key_list.push(key);
								data_fields.push({
										key: key,
										type: 'extra_data'
								});
						}
				});

        if (check_defaults) {
            // Sort by user defined order.
            data_fields.sort(function(a, b) {
                if ($scope.default_columns.indexOf(a.key) < $scope.default_columns.indexOf(b.key)) {
                    return -1;
                } else {
                    return 1;
                }
            });
        } else {
            // Sort alphabetically.
            data_fields.sort(function(a, b) {
                if (a.key.toLowerCase() < b.key.toLowerCase()) {
                    return -1;
                } else {
                    return 1;
                }
            });
        }

        return data_fields;
    };

    /**
     * sets the ``$scope.section`` var to show the proper tab/section of the
     * page.
     * @param {string} section
     */
    $scope.set_location = function (section) {
        $scope.section = section;
    };

    /**
     * returns a number
     */
    $scope.get_number = function ( num ) {
        if ( !angular.isNumber(num) && !_.isNil(num)) {

            return +num.replace(/,/g, '');
        }
        return num;
    };

    $scope.open_update_property_labels_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/update_item_labels_modal.html',
            controller: 'update_item_labels_modal_ctrl',
            resolve: {
                item: function () {
                    return $scope.property;
                },
                type: function() {
                		return "taxlot";
								}
            }
        });
        modalInstance.result.then(
            function () {
                // Grab fresh property data for get_labels()
                property_taxlot_service.get_property($scope.property.id).then(function(property_refresh) {
                    $scope.labels = get_labels(property_refresh);
                });
            },
            function (message) {
               //dialog was 'dismissed,' which means it was cancelled...so nothing to do.
            }
        );
    };



		/**
     * init: sets default state of property detail page,
		 *   sets the field arrays for each section, performs
     *   some date string manipulation for better display rendering,
     *   and gets all the extra_data fields
     *
     */
    var init = function() {

        $scope.taxlot = taxlot_payload.taxlot;

				//Handle formatting for specific property properties (mostly dates)
				// TODO: What are date fields for TaxLot in SEED v2?
        // $scope.taxlot.recent_sale_date = $filter('date')($scope.taxlot.recent_sale_date, 'MM/dd/yyyy');
        // $scope.taxlot.year_ending = $filter('date')($scope.taxlot.year_ending, 'MM/dd/yyyy');
        // $scope.taxlot.release_date = $filter('date')($scope.taxlot.release_date, 'MM/dd/yyyy');
        // $scope.taxlot.generation_date = $filter('date')($scope.taxlot.generation_date, 'MM/dd/yyyy');
        // $scope.taxlot.modified = $filter('date')($scope.taxlot.modified, 'MM/dd/yyyy');
        // $scope.taxlot.created = $filter('date')($scope.taxlot.created, 'MM/dd/yyyy');

        // build columns for current property
        $scope.data_fields = $scope.generate_data_fields($scope.taxlot);
    };
    // fired on controller loaded
    init();
}]);
