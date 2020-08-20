/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 *
 * Controller for the postoffice modal window.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 *
 */
angular.module('BE.seed.controller.postoffice_modal', [])
  .controller('postoffice_modal_controller', [
    '$scope',
    '$log',
    '$uibModalInstance',
    'postoffice_service',
    'property_states',
    'taxlot_states',
    'inventory_type',
    function ($scope, $log, $uibModalInstance, postoffice_service, property_states, taxlot_states, inventory_type) {
    $scope.loading = false;
    $scope.available_templates = [];
    postoffice_service.get_templates().then(function(templates){
      $scope.available_templates = templates;
    });

    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    // Method for passing selected template name, state ids, and inventory type into postoffice_service's 'send_templated_email()' 
    $scope.send_templated_email = function (template_name){
      var inventory_id = property_states.length > 0 ? property_states : taxlot_states;
      console.log("CONTROLLER");
      console.log(template_name);
      console.log("****************");
      console.log(property_states);
      console.log("****************");
      console.log(inventory_type);
      console.log("****************");
      console.log(inventory_id);
      console.log("****************");
      postoffice_service.send_templated_email(template_name, inventory_id, inventory_type);
    }
    }]);

