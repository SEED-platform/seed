angular.module('BE.seed.controller.cleansing', [])
.controller('cleansing_controller', [
  '$scope',
  'cleansingResults',
  function(
    $scope,
    cleansingResults
  ) {
    $scope.name = cleansingResults.name;
    $scope.uploaded = cleansingResults.uploaded;
    $scope.warnings = cleansingResults.warnings;
    $scope.errors = cleansingResults.errors;
}]);

