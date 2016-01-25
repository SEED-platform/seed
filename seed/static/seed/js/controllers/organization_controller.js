/*
 * :copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.organization', [])
.controller('organization_controller', [
    '$scope',
    '$uibModal',
    'users_payload',
    'organization_payload',
    'auth_payload',
    'organization_service',
    'urls',
    function (
      $scope,
      $uibModal,
      users_payload,
      organization_payload,
      auth_payload,
      organization_service,
      urls
    ) {
    $scope.users = users_payload.users;
    $scope.org = organization_payload.organization;
    $scope.auth = auth_payload.auth;

    $scope.new_member_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/new_member_modal.html',
            controller: 'new_member_modal_ctrl'
        });
    };
    $scope.existing_members_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/existing_members_modal.html',
            controller: 'existing_members_modal_ctrl'
        });
    };

    /**
     * open the create a sub org modal
     */
    $scope.create_organization_modal = function() {
        var modalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/create_organization_modal.html',
            controller: 'create_organization_modal_ctrl',
            resolve: {
              organization: function () {
                return $scope.org;
              }
            }
        });
        modalInstance.result.then(
            // modal close()/submit() function
            function () {
                organization_service.get_organization($scope.org.id)
                .then(function (data) {
                    $scope.org = data.organization;
                });
        }, function (message) {
                // dismiss
        });
    };
    }
]);
