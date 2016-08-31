/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.property_detail', [])
		.controller('property_detail_controller', [
			'$controller',
			'$state',
			'$scope',
			'$uibModal',
			'$location',
			'$log',
			'$filter',
			'urls',
			'label_helper_service',
			'inventory_service',
			'property_payload',
			'all_property_columns',
			'default_property_columns',
function($controller, $state, $scope, $uibModal, $location, $log, $filter, urls, label_helper_service,
				 	inventory_service, property_payload, all_property_columns, default_property_columns ) {

	$scope.fields = all_property_columns.fields;

	/** See service for structure of returned payload */
	$scope.inventory = {
		id: property_payload.property.id
	};
	$scope.property = property_payload.property;
	$scope.cycle = property_payload.cycle;
	$scope.related_taxlots = property_payload.taxlots;
	$scope.historical_items = property_payload.history;

	/** Property state is managed in this base scope property. */
	$scope.item_state = property_payload.state;
	$scope.changed_fields = property_payload.changed_fields;

	// The server provides of *all* extra_data keys (across current state and all historical state)
	// Let's remember this.
	$scope.all_extra_data_keys = property_payload.extra_data_keys;

	$scope.inventory_type = "properties";
	$scope.item_title = "Property : " + ($scope.item_state.address_line_1 ? $scope.item_state.address_line_1 : '(no address 1)');
	$scope.user = {};
	$scope.user_role = property_payload.user_role;



	/** Instantiate 'parent' controller class,
	 *  where the more generic methods for editing a detail item are located.
	 *  (Methods in this child class are more specific to a 'Property' detail item.) */
	$controller('base_detail_controller', { $scope: $scope, $uibModal: $uibModal,
																					$log: $log, inventory_service: inventory_service,
																					all_columns: all_property_columns, urls: urls, $filter: $filter,
																					label_helper_service: label_helper_service,
																					default_columns: default_property_columns });



	/**
	 * User clicked 'save' button
	 */
	$scope.on_save = function () {
		$scope.save_property();
	};

	$scope.on_show_related_taxlot = function(taxlot) {
		$location.path('/taxlots/' + taxlot.taxlot.id + '/cycles/' + taxlot.cycle.id);
	};


	/**
	 * save_property: saves the user's changes to the Property State object.
	 */
	$scope.save_property = function (){
		$scope.$emit('show_saving');
		inventory_service.update_property($scope.property.id, $scope.cycle.id, $scope.item_state)
			.then(function (data){
					// In the short term, we're just refreshing the page after a save so the table
					// shows new history.
					// TODO: Refactor so that table is dynamically updated with new information
					$scope.$emit('finished_saving');
					$state.reload();
				}, function (data, status){
					// reject promise
					$scope.$emit('finished_saving');
				}
			).catch(function (data){
				$log.error( String(data) );
			});
	};

	/**
	 *   init: sets default state of property detail page,
	 *   sets the field arrays for each section, performs
	 *   some date string manipulation for better display rendering,
	 *   and gets all the extra_data fields
	 *
	 */
	var init = function() {

		$scope.format_date_values($scope.item_state, inventory_service.property_state_date_columns);

		$scope.data_fields = $scope.generate_data_fields($scope.item_state, $scope.default_property_columns, $scope.all_extra_data_keys);

		$scope.labels = $scope.init_labels($scope.property);

	};

	// fired on controller loaded
	init();

}]);
