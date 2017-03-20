/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.create_sub_organization_modal', [])
.controller('create_sub_organization_modal_controller', [
    '$scope',
    '$uibModalInstance',
    'organization_service',
    'organization',
    function ($scope, $uibModalInstance, organization_service, organization) {
        $scope.sub_org = {};
        $scope.error_message = '';

      /**
     * creates a sub organization with an owner
     * @param  {Boolean} is_valid whether the form is valid (checked in the html)
     */
    $scope.submit_form = function(is_valid) {
      organization_service.create_sub_org(organization, $scope.sub_org)
        .then(function(data){
            // resolve promise
            $uibModalInstance.close();

        }, function(data) {
            // reject promise
            $scope.error_message = data.message;
        });
    };


    $scope.close = function () {
        $uibModalInstance.close();
    };

    $scope.cancel = function () {
        $uibModalInstance.dismiss('cancel');
    };

    /**
     * set the focus on the first input box
     */
    _.delay(function() {
        angular.element('#createOrganizationName').focus();
    }, 50);

    /**
     * clear the error message when the user starts typing
     */
    $scope.$watch('sub_org.email', function(){
        $scope.error_message = '';
    });
}]);
