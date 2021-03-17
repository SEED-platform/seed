angular.module('BE.seed.controller.geocode_modal', [])
  .controller('geocode_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'geocode_service',
    'inventory_type',
    'org_id',
    'organization_service',
    'property_view_ids',
    'taxlot_view_ids',
    function ($scope, $uibModalInstance, geocode_service, inventory_type, org_id, organization_service, property_view_ids, taxlot_view_ids) {
      $scope.inventory_type = inventory_type;
      $scope.property_view_ids = _.uniq(property_view_ids);
      $scope.taxlot_view_ids = _.uniq(taxlot_view_ids);
      $scope.geocode_state = 'verify';

      geocode_service.check_org_has_api_key(org_id).then(function (result) {
        $scope.has_api_key = result;
      });

      geocode_service.check_org_has_geocoding_enabled(org_id).then(function (result) {
        $scope.geocoding_enabled = result;
      });

      organization_service.geocoding_columns(org_id).then(function (data) {
        if ($scope.inventory_type === 'properties') {
          $scope.has_enough_geocoding_columns = data.PropertyState.length > 0;
        } else if ($scope.inventory_type === 'taxlots') {
          $scope.has_enough_geocoding_columns = data.TaxLotState.length > 0;
        }
      });

      geocode_service.confidence_summary($scope.property_view_ids, $scope.taxlot_view_ids).then(function (result) {
        if (result.properties) {
          $scope.pre_properties_not_geocoded = result.properties.not_geocoded;

          $scope.pre_properties_geocoded_high_confidence = result.properties.high_confidence;
          $scope.pre_properties_geocoded_low_confidence = result.properties.low_confidence;
          $scope.pre_properties_geocoded_manually = result.properties.manual;
          $scope.pre_properties_geocode_not_possible = result.properties.missing_address_components;
        }

        if (result.tax_lots) {
          $scope.pre_tax_lots_not_geocoded = result.tax_lots.not_geocoded;

          $scope.pre_tax_lots_geocoded_high_confidence = result.tax_lots.high_confidence;
          $scope.pre_tax_lots_geocoded_low_confidence = result.tax_lots.low_confidence;
          $scope.pre_tax_lots_geocoded_manually = result.tax_lots.manual;
          $scope.pre_tax_lots_geocode_not_possible = result.tax_lots.missing_address_components;
        }
      });

      $scope.geocode_buildings = function () {
        $scope.geocode_state = 'geocoding';

        geocode_service.geocode_by_ids($scope.property_view_ids, $scope.taxlot_view_ids).then(function () {
          geocode_service.confidence_summary($scope.property_view_ids, $scope.taxlot_view_ids).then(function (result) {
            if (result.properties) {
              $scope.properties_geocoded_high_confidence = result.properties.high_confidence;
              $scope.properties_geocoded_low_confidence = result.properties.low_confidence;
              $scope.properties_geocoded_manually = result.properties.manual;
              $scope.properties_geocode_not_possible = result.properties.missing_address_components;
            }

            if (result.tax_lots) {
              $scope.tax_lots_geocoded_high_confidence = result.tax_lots.high_confidence;
              $scope.tax_lots_geocoded_low_confidence = result.tax_lots.low_confidence;
              $scope.tax_lots_geocoded_manually = result.tax_lots.manual;
              $scope.tax_lots_geocode_not_possible = result.tax_lots.missing_address_components;
            }

            $scope.geocode_state = 'result';
          });
        }).catch(function (e) {
          $scope.geocode_state = 'fail';
          if (e.message == 'MapQuestAPIKeyError') $scope.error_message = 'MapQuest API key may be invalid or at its limit.';
          else $scope.error_message = e.statusText;
        });
      };

      /**
       * cancel: dismisses the modal
       */
      $scope.cancel = function () {
        $uibModalInstance.dismiss({
          geocode_state: $scope.geocode_state,
          property_view_ids: $scope.property_view_ids,
          taxlot_view_ids: $scope.taxlot_view_ids
        });
      };

      /**
       * close: closes the modal
       */
      $scope.close = function () {
        $uibModalInstance.close({
          geocode_state: $scope.geocode_state,
          property_view_ids: $scope.property_view_ids,
          taxlot_view_ids: $scope.taxlot_view_ids
        });
      };
    }]);
