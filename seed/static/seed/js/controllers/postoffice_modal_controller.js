/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 *
 * Controller for the Update Labels modal window.
 * Manages applying labels to a single Property or Tax Lot, as
 * well as allowing for the creation of new labels.
 * The Property or Tax Lot ID is passed in as 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 *
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
    function ($scope, $log, $uibModalInstance, postoffice_service, property_states, taxlot_states) {
    $scope.loading = false;
    $scope.available_templates = [];
    postoffice_service.get_templates().then(function(templates){
      $scope.available_templates = templates;
    });

    $scope.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };

    $scope.send_templated_email = function (template_name){
      var building_id = property_states.length > 0 ? property_states : taxlot_states;
      console.log("CONTROLLER");
      console.log(template_name);
      console.log("****************");
      console.log(property_states);
      console.log("****************");
      console.log(building_id);
      postoffice_service.send_templated_email(template_name, building_id);
    }
    }]);

