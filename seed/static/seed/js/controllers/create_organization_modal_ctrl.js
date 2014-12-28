/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.create_organization_modal', [])
.controller('create_organization_modal_ctrl', [
    '$scope',
    '$modalInstance',
    'organization_service',
    'organization',
    '$timeout',
    function ($scope, $modalInstance, organization_service, organization, $timeout) {
        $scope.sub_org = {};
        $scope.error_message = "";

      /**
     * creates a sub organization with an owner
     * @param  {Boolean} is_valid whether the form is valid (checked in the html)
     */
    $scope.submit_form = function(is_valid) {
      organization_service.create_sub_org(organization, $scope.sub_org)
        .then(function(data){
            // resolve promise
            $modalInstance.close();

        }, function(data) {
            // reject promise
            $scope.error_message = data.message;
        });
    };
    
    
    $scope.close = function () {
        $modalInstance.close();
    };

    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };

    /**
     * set the focus on the first input box
     */
    $timeout(function() {
        angular.element('#createOrganizationName').focus();
    }, 50);

    /**
     * clear the error message when the user starts typing
     */
    $scope.$watch('sub_org.email', function(){
        $scope.error_message = "";
    });
}]);
