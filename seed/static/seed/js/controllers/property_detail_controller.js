/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.property_detail', [])
		.controller('property_detail_controller', [
			'$controller',
			'$scope',
			'$uibModal',
			'$log',
			'$filter',
			'urls',
			'label_helper_service',
			'property_taxlot_service',
			'property_payload',
			'all_property_columns',
			'default_property_columns',
function($controller, $scope, $uibModal, $log, $filter, urls, label_helper_service,
				 	property_taxlot_service, property_payload, all_property_columns, default_property_columns ) {

	$scope.property = property_payload;

	/** Property state is managed in this base scope property. */
	$scope.item_state = property_payload.state;

	$scope.item_type = "property";
	$scope.item_title = "Property : " + $scope.property.state.address_line_1;
	$scope.user = {};
	$scope.user_role = property_payload.user_role;



	/** Instantiate 'parent' controller class,
	 *  where the more generic methods for editing a detail item are located.
	 *  (Methods in this child class are more specific to a 'Property' detail item.) */
	$controller('base_detail_controller', { $scope: $scope, $uibModal: $uibModal,
																					$log: $log, property_taxlot_service: property_taxlot_service,
																					all_columns: all_property_columns, urls: urls, $filter: $filter,
																					label_helper_service: label_helper_service,
																					default_columns: default_property_columns });



	/* User clicked 'save' button */
	$scope.on_save = function () {
		$scope.save_property();
	}


	/**
	 * save_property: saves the user's changes to the Property State object.
	 */
	$scope.save_property = function (){
		$scope.$emit('show_saving');
		property_taxlot_service.update_property($scope.property.id, $scope.property.cycle.id, $scope.item_state)
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

		$scope.format_date_values($scope.item_state, property_taxlot_service.property_state_date_columns);

		$scope.data_fields = $scope.generate_data_fields($scope.item_state, $scope.default_property_columns);

		$scope.labels = $scope.init_labels($scope.property);

	};

	// fired on controller loaded
	init();

}]);
