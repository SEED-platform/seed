/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.new_member_modal', [])
.controller('new_member_modal_ctrl', [
  '$scope',
  '$modalInstance',
  'organization',
  'user_service',
  '$timeout',
  function ($scope, $modalInstance, organization, user_service, $timeout) {
    $scope.roles = [
      {
        name: "Member",
        value: "member"
      },
      {
        name: "Owner",
        value: "owner"
      },
      {
        name: "Viewer",
        value: "viewer"
      }
    ];
    $scope.user = {};
    $scope.user.role = $scope.roles[0];
    $scope.user.organization = organization;

    /**
     * adds a user to the org
     * @param  {Boolean} is_valid whether the form is valid (checked in the html)
     */
    $scope.submit_form = function(is_valid) {
      user_service.add($scope.user).then(function(data){
            // resolve promise
            $modalInstance.close();

        }, function(data) {
            // reject promise
             $scope.$emit('app_error', data);
        });
    };
    
    $scope.close = function () {
        $modalInstance.close();
    };

    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };

    $timeout(function(name) {
      angular.element('#newMemberFirstName').focus();
    }, 50); 
}]);

angular.module('BE.seed.controller.existing_members_modal', [])
.controller('existing_members_modal_ctrl', [
  '$scope',
  '$modalInstance',
  function ($scope, $modalInstance) {
    
    $scope.close = function () {
        $modalInstance.close();
    };

    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };
}]);
