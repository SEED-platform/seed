/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.email_templates_modal', [])
    .controller('email_templates_modal_controller', [
        '$scope', 
        'postoffice_service',
        '$uibModalInstance', 
        'action', 
        'data', 
        function (
            $scope,
            postoffice_service,
            $uibModalInstance,
            action,
            data,
        ) {
            $scope.action = action;
            $scope.data = data;
            $scope.rename_template = function () {
                if (!$scope.disabled()) {
                    var id = $scope.data.id;
                    var template = _.omit($scope.data, 'id');
                    template.name = $scope.newName;
                    postoffice_service.update_template(id, template).then(function (result) {
                        $uibModalInstance.close(result.name);
                    }).catch(function () {
                        $uibModalInstance.dismiss();
                    });
                }
            };

            $scope.remove_template = function () {
                postoffice_service.remove_template($scope.data.id).then(function () {
                    $uibModalInstance.close();
                }).catch(function () {
                    $uibModalInstance.dismiss();
                });
            };

            $scope.disabled = function () {
                if ($scope.action === 'rename') {
                    return _.isEmpty($scope.newName) || $scope.newName === $scope.data.name;
                } else if ($scope.action === 'new') {
                    return _.isEmpty($scope.newName);
                }
            };

            $scope.cancel = function () {
                $uibModalInstance.dismiss();
            };
        }]);