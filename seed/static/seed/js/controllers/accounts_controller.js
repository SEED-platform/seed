/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.accounts', [])
.controller('accounts_controller', [
    '$scope',
    '$uibModal',
    'organization_payload',
    'urls',
    'organization_service',
    function ($scope, $uibModal, organization_payload, urls, organization_service) {
    
    $scope.create_organization_modal = function(org) {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/create_organization_modal.html',
            controller: 'create_organization_modal_ctrl',
            resolve: {
              organization: function () {
                return org;
              }
            }
        });
        modalInstance.result.then(
            // modal close()/submit() function
            function () {
                organization_service.get_organizations()
                .then(function (data) {
                    organization_payload = data;
                    init();
                });
        }, function (message) {
                // dismiss
        });
    };
    
    var init = function(){
        $scope.orgs = organization_payload.organizations;
        $scope.orgs_I_own = organization_payload.organizations.filter(function (o) {
            return o.user_is_owner;
        });
    };
    init();

}
]);
