/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.ubid_editor_modal', [])
    .controller('ubid_editor_modal_controller', [
        '$scope',
        '$state',
        '$uibModalInstance',
        function (
            $scope,
            $state,
            $uibModalInstance,
        ) {
            $scope.modal_text = 'UBID MODEL EDITOR';
            $scope.close = function () {
                $uibModalInstance.close({
                });
            };

        }
    ]
)