angular.module('BE.seed.controller.email_templates_modal', [])
    .controller('email_templates_modal_controller', [
        '$scope', //from before
        'postoffice_service',
        '$uibModalInstance', //?
        'action', //new_group
        // 'inventory_service', //from before
        // inventory_type', //new_group
        'data', //new_group
        // 'org_id', //new_group
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
                console.log("Reached the rename modal controller");
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
                console.log("Reached the remove modal controller");
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