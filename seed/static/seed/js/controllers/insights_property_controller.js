angular.module('BE.seed.controller.insights_property', [])
  .controller('insights_property_controller', [
    '$scope',
    '$stateParams',
    '$uibModal',
    'urls',
    'cycles',
    function (
      $scope,
      $stateParams,
      $uibModal,
      urls,
      cycles
    ) {

      $scope.id = $stateParams.id;
      $scope.cycles = cycles.cycles;
     }
  ]);
