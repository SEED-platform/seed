/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.property_detail', [])
		.controller('property_detail_controller', [
			'$controller',
			'$scope',
			'$routeParams',
			'$uibModal',
			'$log',
			'$filter',
			'$location',
			'property_taxlot_service',
			'property_payload',
			'all_columns',
			'urls',
			'label_helper_service',
			'default_columns',
function($controller, $scope, $routeParams, $uibModal, $log, $filter, $location,
				 	property_taxlot_service, property_payload, all_columns, urls,  label_helper_service, default_columns) {


	$scope.item_type = "property";
	$scope.property = property_payload;
	$scope.page_title = $scope.property.state.address_line_1
	$scope.user = {};
	$scope.user_role = property_payload.user_role;

	/** Instantiate 'parent' controller class,
	 *  where the more generic methods for a detail item are located.
	 *  (Methods in this child class are more specific to a 'Property' detail item.) */
	$controller('base_detail_controller', { $scope: $scope, $routeParams: $routeParams, $uibModal: $uibModal,
																															$log: $log, property_taxlot_service: property_taxlot_service,
																															all_columns: all_columns, urls: urls, $filter: $filter,
																															$location: $location, label_helper_service: label_helper_service,
																															default_columns: default_columns });


	/* User clicked 'save' button */
	$scope.on_save = function () {
		$scope.save_property();
	}


	/**
	 * restore_property: restores the property from its copy
	 *   and hides the edit fields
	 */
	$scope.restore_copy = function () {
		$scope.property = $scope.item_copy;
		$scope.edit_form_showing = false;
	};


	/**
	 * save_property: saves the property's updates
	 */
	$scope.save_property = function (){
		$scope.$emit('show_saving');
		property_taxlot_service.update_property($scope.property.id, $scope.property.cycle.id, $scope.user_org_id, $scope.property.state)
			.then(function (data){
					$scope.$emit('finished_saving');
				}, function (data, status){
					// reject promise
					$scope.$emit('finished_saving');
				}
			).catch(function (data){
				$log.error( String(data) );
			});
	};

	/**
	 * init: sets default state of property detail page,
	 *   sets the field arrays for each section, performs
	 *   some date string manipulation for better display rendering,
	 *   and gets all the extra_data fields
	 *
	 */
	var init = function() {

		// format date column values
		$scope.format_date_values($scope.property.state, property_taxlot_service.property_state_date_columns);

		// build columns for current Property
		$scope.data_fields = $scope.generate_data_fields($scope.property.state, $scope.default_columns);

		$scope.labels = $scope.init_labels($scope.property);
	};

	// fired on controller loaded
	init();

}]);
