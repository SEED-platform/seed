angular.module('BE.seed.controller.insights_program', [])
  .controller('insights_program_controller', [
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
