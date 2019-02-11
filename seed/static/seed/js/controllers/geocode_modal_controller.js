angular.module('BE.seed.controller.geocode_modal', [])
  .controller('geocode_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'geocode_service',
    'org_id',
    'property_state_ids',
    'taxlot_state_ids',
    function ($scope, $uibModalInstance, geocode_service, org_id, property_state_ids, taxlot_state_ids) {
      $scope.property_state_ids = _.uniq(property_state_ids);
      $scope.taxlot_state_ids = _.uniq(taxlot_state_ids);

      geocode_service.check_org_has_api_key(org_id).then(function (result) {
        if (result) {
          $scope.geocode_state = 'verify';
        } else {
          $scope.geocode_state = 'no_key';
        }
      });

      geocode_service.confidence_summary($scope.property_state_ids, $scope.taxlot_state_ids).then(function (result) {
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
          $scope.pre_tax_lots_geocode_not_possible = result.tax_lots.missing_address_components;
        }
      });

      $scope.geocode_buildings = function () {
        $scope.geocode_state = 'geocoding';

        geocode_service.geocode_by_ids($scope.property_state_ids, $scope.taxlot_state_ids).then(function () {
          geocode_service.confidence_summary($scope.property_state_ids, $scope.taxlot_state_ids).then(function (result) {
            if (result.properties) {
              $scope.properties_geocoded_high_confidence = result.properties.high_confidence;
              $scope.properties_geocoded_low_confidence = result.properties.low_confidence;
              $scope.properties_geocoded_manually = result.properties.manual;
              $scope.properties_geocode_not_possible = result.properties.missing_address_components;
            }

            if (result.tax_lots) {
              $scope.tax_lots_geocoded_high_confidence = result.tax_lots.high_confidence;
              $scope.tax_lots_geocoded_low_confidence = result.tax_lots.low_confidence;
              $scope.tax_lots_geocode_not_possible = result.tax_lots.missing_address_components;
            }

            $scope.geocode_state = 'result';
          });
        });
      };

      /**
       * cancel: dismisses the modal
       */
      $scope.cancel = function () {
        $uibModalInstance.dismiss({
          geocode_state: $scope.geocode_state,
          property_state_ids: $scope.property_state_ids,
          taxlot_state_ids: $scope.taxlot_state_ids
        });
      };

      /**
       * close: closes the modal
       */
      $scope.close = function () {
        $uibModalInstance.close({
          geocode_state: $scope.geocode_state,
          property_state_ids: $scope.property_state_ids,
          taxlot_state_ids: $scope.taxlot_state_ids
        });
      };
    }]);
