/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_admin', [])
  .controller('ubid_admin_controller', [
    '$scope',
    '$stateParams',
    'ubid_service',
    'simple_modal_service',
    '$uibModal',
    'urls',
    function (
      $scope,
      $stateParams,
      ubid_service,
      simple_modal_service,
      $uibModal,
      urls
    ) {
      let view_id;
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.item_state = $scope.inventory_payload.state;
      const state_id = $scope.inventory_payload.state.id;

      // Allows this controller be reused by the inventory detail and inventory list
      // Inventory Detail
      if ('view_id' in $stateParams) {
        view_id = $stateParams.view_id;
        // Inventory List
      } else {
        view_id = $scope.property_view_id || $scope.taxlot_view_id;
      }

      const inventory_key = $scope.inventory_type === 'properties' ? 'property' : 'taxlot';

      const refresh_ubids = () => {
        return ubid_service.get_ubid_models_by_state(view_id, inventory_key).then(results => {
          if ('data' in results) {
            $scope.ubids = results.data.sort(({preferred}) => preferred ? -1 : 1);
          } else {
            $scope.message = results.message;
          }
        });
      };


      $scope.edit_or_create = (ubid = false) => {
        const ubid_editor_modal = $uibModal.open({
          backdrop: 'static',
          templateUrl: urls.static_url + 'seed/partials/ubid_editor_modal.html',
          controller: 'ubid_editor_modal_controller',
          resolve: {
            ubid: () => ubid,
            ubids: () => ubid_service.get_ubid_models_by_state(view_id, inventory_key).then(results => results.data),
            state_id: () => state_id,
            view_id: () => view_id,
            inventory_key: () => inventory_key
          }
        });
        ubid_editor_modal.result.then(async () => {
          await refresh_ubids();
          $scope.$emit('reload');
        });
      };

      $scope.delete_ubid = (ubid, ubid_id) => {
        const modalOptions = {
          type: 'default',
          okButtonText: 'Yes',
          cancelButtonText: 'Cancel',
          headerText: 'Are you sure?',
          bodyText: `You're about to permanently delete the UBID "${ubid}". Would you like to continue?`
        };
        simple_modal_service.showModal(modalOptions).then(() => {
          // user confirmed, delete it
          ubid_service.delete_ubid(ubid_id).then(async () => {
            await refresh_ubids();
            $scope.$emit('reload');
          }).catch((err) => {
            console.log(`Error attempting to delete ubid id: ${ubid_id}`);
            console.log('Error', err);
          });
        }, () => {
          // user cancels
        });
      };

      // init
      refresh_ubids();
    }
  ]);
