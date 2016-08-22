/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.base_detail', [])
		.controller('base_detail_controller', [
			'$scope',
			'$uibModal',
			'$log',
			'$filter',
			'property_taxlot_service',
			'all_columns',
			'urls',
			'label_helper_service',
			'default_columns',
function($scope, $uibModal, $log, $filter, property_taxlot_service,
				 all_columns, urls, label_helper_service, default_columns) {

	$scope.fields = all_columns.fields;
	$scope.default_columns = default_columns.columns;
	$scope.edit_form_showing = false;

	/** Holds a copy of original state of item_state.
	 *  Used when 'Cancel' is selected and item should be
	 *  returned to original state. */
	$scope.item_copy = {};

	/** An array of fields to show to user,
	 *  populated according to settings.*/
	$scope.data_fields = [];


	$scope.status = {
		isopen: false
	};

	$scope.init_labels = function(item) {
		return _.map(item.labels, function(lbl) {
			lbl.label = label_helper_service.lookup_label(lbl.color);
			return lbl;
		});
	};

	/* User clicked 'cancel' button */
	$scope.on_cancel = function () {
		$scope.restore_copy();
		$scope.edit_form_showing = false;
	}

	/* User clicked 'edit' link */
	$scope.on_edit = function () {
		$scope.make_copy_before_edit();
		$scope.edit_form_showing = true;
	}

	/**
	 * save_property_state: saves the property state in case cancel gets clicked
	 */
	$scope.make_copy_before_edit = function () {
		$scope.item_copy = angular.copy($scope.item_state);
	};

	/**
	 * restore_property: restores the property state from its copy
	 */
	$scope.restore_copy = function () {
		$scope.item_state = $scope.item_copy;
	};



	/**
	 * generate_data_fields: returns a list of objects representing
	 * the data fields (fixed column and extra_data) to show for
	 * the current item in the detail view (Proeprty or State).
	 *
	 * This method makes sure keys/fields are not duplicated.
	 * Also, it only adds columns that are in the
	 * default_columns property (if any exist).
	 *
	 * @param {Object}	stateObj: A 'state' object (for a Property or TaxLot) of key/value pairs
	 *
	 * @returns {Array} data_fields: A list of data_field objects
	 *
	 */
	$scope.generate_data_fields = function(stateObj, default_columns) {

		var data_fields = [];
		var key_list = [];
		var check_defaults = (default_columns && default_columns.length > 0);

		// add fixed_column property properties to data_fields
		angular.forEach(stateObj, function ( val, key ) {
			// Duplicate check and check if default_columns is used and if field in columns
			if ( !_.isUndefined(val) && $scope.is_valid_data_column_key(key) && !_.includes(key_list, key) &&
					(!check_defaults || (check_defaults && _.includes(default_columns, key)))) {
				key_list.push(key);
				data_fields.push({
					key: key,
					type: 'fixed_column'
				});
			}
		});

		// add extra_data properties for property to data_fields
		angular.forEach(stateObj.extra_data, function (val, key){
			// Duplicate check and check if default_columns is used and if field in columns
			if (!_.isUndefined(val) && $scope.is_valid_data_column_key(key) && !_.includes(key_list, key) &&
					(!check_defaults || (check_defaults && _.includes(default_columns, key)))) {
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
				if (default_columns.indexOf(a.key) < default_columns.indexOf(b.key)) {
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
     * is_valid_key: checks to see if the key or attribute should be excluded
     *   from being copied from parent to master building
		*
		*    TODO Update these for v2...I've removed keys that were obviously old (e.g. canonical)
     */
    $scope.is_valid_data_column_key = function (key) {
        var known_invalid_keys = [
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
	 * returns a number
	 */
	$scope.get_number = function ( num ) {
		if ( !angular.isNumber(num) && !_.isNil(num)) {
			return +num.replace(/,/g, '');
		}
		return num;
	};

	/** Open a model to edit labels for the current detail item.
	 *
	 * @param item	A Propety or TaxLot object
	 * @param type	"property" or "taxlot"  << This might be unnecessary.
	 */

	$scope.open_update_labels_modal = function(item, type) {
		var modalInstance = $uibModal.open({
			templateUrl: urls.static_url + 'seed/partials/update_item_labels_modal.html',
			controller: 'update_item_labels_modal_ctrl',
			resolve: {
				item: function () {
					return item;
				},
				type: function() {
					return type;
				}
			}
		});
		modalInstance.result.then(
				function () {
					// TODO: Update this code based on old building objects to fresh labels after applied
					// Grab fresh property data for get_labels()
					//property_taxlot_service.get_property($scope.property.id).then(function(property_refresh) {
					//	$scope.labels = get_labels(property_refresh);
					//});
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

}]);
