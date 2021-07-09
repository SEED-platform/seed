/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

/**
 * Controller for the postoffice modal window.
 * The selected Property IDs or Tax Lot IDs are passed into 'inventory_id', identified by
 * inventory_type="properties" or inventory_type="taxlots"
 */
angular.module('BE.seed.controller.postoffice_modal', [])
  .controller('postoffice_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'postoffice_service',
    'property_states',
    'taxlot_states',
    'inventory_type',
    function ($scope, $uibModalInstance, postoffice_service, property_states, taxlot_states, inventory_type) {
      $scope.loading = false;
      $scope.available_templates = [];

      postoffice_service.get_templates().then(function(templates){
        $scope.available_templates = templates;
      });
      $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
      };

      // Method for passing selected template name, state ids, and inventory type into postoffice_service's 'send_templated_email()'
      $scope.send_templated_email = function (template_id){
        var inventory_id = property_states.length > 0 ? property_states : taxlot_states;
        postoffice_service.send_templated_email(template_id, inventory_id, inventory_type).then(function(result) {
          $uibModalInstance.close(result);
        });
      };
    }]);

