/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.taxlot_detail', [])
		.controller('taxlot_detail_controller', [
			'$controller',
			'$state',
			'$scope',
			'$uibModal',
			'$location',
			'$log',
			'$filter',
			'urls',
			'label_helper_service',
			'property_taxlot_service',
			'taxlot_payload',
			'all_taxlot_columns',
			'default_taxlot_columns',
function($controller, $state, $scope,  $uibModal, $location, $log, $filter, urls, label_helper_service,
				 	property_taxlot_service, taxlot_payload, all_taxlot_columns, default_taxlot_columns ) {

	/** See service for structure of returned payload */
	$scope.taxlot = taxlot_payload.taxlot;
	$scope.cycle = taxlot_payload.cycle;
	$scope.related_properties = taxlot_payload.properties;
	$scope.historical_items = taxlot_payload.history;

	/** TaxLot state is managed in this base scope property. */
	$scope.item_state = taxlot_payload.state;
	$scope.changed_fields = taxlot_payload.changed_fields;

	// Remember the list of *all* extra_data keys (current state or historical state)
	// as provided by the server.
	$scope.all_extra_data_keys = taxlot_payload.extra_data_keys;

	$scope.item_type = "taxlot";
	$scope.item_title = "Tax Lot : " + $scope.item_state.address_line_1 // TODO: Decide what value (address_line_1?) to show as identifying label in tax lot detail view?
	$scope.user = {};
	$scope.user_role = taxlot_payload.user_role;


	/** Instantiate 'parent' controller class,
	 *  where the more generic methods for a detail item are located.
	 *  (Methods in this child class are more specific to a 'Tax Lot' detail item.) */
	$controller('base_detail_controller', { $scope: $scope, $uibModal: $uibModal,
																					$log: $log, property_taxlot_service: property_taxlot_service,
																					all_columns: all_taxlot_columns, urls: urls, $filter: $filter,
																					label_helper_service: label_helper_service,
																					default_columns: default_taxlot_columns });


	/* User clicked 'save' button */
	$scope.on_save = function () {
		$scope.save_taxlot();
	}


	$scope.on_show_related_property = function(property) {
		$location.path('/properties/' + property.property.id + '/cycles/' + property.cycle.id);
	}

	/**
	 * save_taxlot: saves the user's changes to the TaxLot State object.
	 */
	$scope.save_taxlot = function (){
		$scope.$emit('show_saving');
		property_taxlot_service.update_taxlot($scope.taxlot.id, $scope.cycle.id, $scope.item_state)
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
	 * init: sets default state of Tax Lot Detail page,
	 *   sets the field arrays for each section, performs
	 *   some date string manipulation for better display rendering,
	 *   and gets all the extra_data fields
	 *
	 */
	var init = function() {

		$scope.format_date_values($scope.item_state, property_taxlot_service.taxlot_state_date_columns);

		$scope.data_fields = $scope.generate_data_fields($scope.item_state, $scope.default_taxlot_columns, $scope.all_extra_data_keys);

		$scope.labels = $scope.init_labels($scope.taxlot);
	};

	// fired on controller loaded
	init();

}]);
