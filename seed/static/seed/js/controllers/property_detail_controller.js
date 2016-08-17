/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.property_detail_controller', [])
		.controller('property_detail_controller', [
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
function($scope, $routeParams, $uibModal, $log, property_taxlot_service, property_payload, all_columns, urls, $filter, $location, label_helper_service, default_columns) {
	$scope.user = {};
	$scope.user.property_id = $routeParams.property_id;
	$scope.property = property_payload;

	//$scope.user_role = property_payload.user_role;
	//$scope.user_org_id = property_payload.user_org_id;

	$scope.fields = all_columns.fields;
	$scope.default_columns = default_columns.columns;

	/** Holds a copy of original state of Property. Used
	 *  when 'Cancel' is selected and Property should be
	 *  returned to original state. */
	$scope.property_copy = {};

	/** An array of fields to show to user,
	 *  populated according to settings.*/
	$scope.data_fields = [];


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
	$scope.labels = get_labels($scope.property);


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
	 * save_property: saves the property's updates
	 */
	$scope.save_property = function (){
		$scope.$emit('show_saving');
		property_taxlot_service.update_property($scope.property, $scope.user_org_id)
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
	 *   DMCQ TODO: Remove any of these that no longer apply in BLUESKY
	 *   Already removed canonical_building and similar...
	 *
	 */
	$scope.is_valid_data_column_key = function (key) {
		var known_invalid_keys = [
			'id',
			'cycle',
			'organization_id',
			'best_guess_confidence',
			'best_guess_canonical_building',
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
			'duplicate'
		];
		var no_invalid_key = !_.includes(known_invalid_keys, key);

		return (!_.includes(key, '_source') && !_.includes(key, 'extra_data') && !_.includes(key, '$$') && no_invalid_key);
	};


	/**
	 * generate_data_fields: returns a list of objects representing
	 * the data fields (fixed column and extra_data) to show for
	 * the given 'property.'
	 * This method makes sure keys/fields are not duplicated.
	 * Also, this method only adds columns that are in the
	 * default_columns property for the current user (if any exist).
	 *
	 * @param {Object}	property: A Property object
	 *
	 * @returns {Array} data_fields: A list of data_field objects
	 *
	 */
	$scope.generate_data_fields = function() {
		var data_fields = [];
		var key_list = [];
		var check_defaults = !!$scope.default_columns.length;

		var property_state = $scope.property.state;

		// add fixed_column property properties to data_fields
		angular.forEach(property_state, function ( val, key ) {
			// Duplicate check and check if default_columns is used and if field in columns
			if ( !_.isUndefined(val) && $scope.is_valid_data_column_key(key) && !_.includes(key_list, key) &&
					(!check_defaults || (check_defaults && _.includes($scope.default_columns, key)))) {
				key_list.push(key);
				data_fields.push({
					key: key,
					type: 'fixed_column'
				});
			}
		});

		// add extra_data properties for property to data_fields
		angular.forEach(property_state.extra_data, function (val, key){
			// Duplicate check and check if default_columns is used and if field in columns
			if (!_.isUndefined(val) && $scope.is_valid_data_column_key(key) && !_.includes(key_list, key) &&
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
					return "property";
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
	 * Iterate through all object values and format
	 * those we recognize as a 'date' value
	 */

	$scope.format_date_values = function(stateObj, date_columns) {

		if (!stateObj || stateObj.length===0) return;
		if (!date_columns || date_columns.length===0) return;

		// Look for each 'date' type value in all Property State values
		// and update format accordingly.
		_.each(date_columns, function(key){
			if(stateObj[key]){
				stateObj[key] = $filter('date')(stateObj[key], 'MM/dd/yyyy');
			}
		});

	}


	/**
	 * init: sets default state of property detail page,
	 *   sets the field arrays for each section, performs
	 *   some date string manipulation for better display rendering,
	 *   and gets all the extra_data fields
	 *
	 */
	var init = function() {

		// TODO: What date fields do we need to format for Property in SEED v2?
		//Handle formatting for specific property properties (mostly dates)
		// These are the building properties that we used to format....
		/*
		 $scope.property.recent_sale_date = $filter('date')($scope.property.recent_sale_date, 'MM/dd/yyyy');
		 $scope.property.year_ending = $filter('date')($scope.property.year_ending, 'MM/dd/yyyy');
		 $scope.property.release_date = $filter('date')($scope.property.release_date, 'MM/dd/yyyy');
		 $scope.property.generation_date = $filter('date')($scope.property.generation_date, 'MM/dd/yyyy');
		 $scope.property.modified = $filter('date')($scope.property.modified, 'MM/dd/yyyy');
		 $scope.property.created = $filter('date')($scope.property.created, 'MM/dd/yyyy');
		 */

		// format date column values
		$scope.format_date_values($scope.property.state, property_taxlot_service.property_state_date_columns);

		// build columns for current Property
		$scope.data_fields = $scope.generate_data_fields();
	};
	// fired on controller loaded
	init();
}]);
