angular.module('BE.seed.controller.cleansing', [])
.controller('cleansing_controller', [
  '$scope',
  '$modalInstance',
  'cleansingResults',
  'name',
  'uploaded',
  function(
    $scope,
    $modalInstance,
    cleansingResults,
    name,
    uploaded
  ) {
    $scope.name = name;
    $scope.uploaded = uploaded;

    if (Object.keys(cleansingResults).length > 0) {
      $scope.warnings = cleansingResults.warnings;
      $scope.errors = cleansingResults.errors;
    } else {
      $scope.warnings = [];
      $scope.errors = [];
    }

    $scope.total = $scope.warnings.length + $scope.errors.length;
    console.log('Total Warnings/Errors:', $scope.total);
    console.log(cleansingResults);

    $scope.close = function() {
      $modalInstance.close();
    }
}]);

