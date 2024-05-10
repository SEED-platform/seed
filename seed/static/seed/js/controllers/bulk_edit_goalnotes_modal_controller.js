/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.controller.bulk_edit_goalnotes_modal', [])
  .controller('bulk_edit_goalnotes_modal_controller', [
    '$scope',
    '$state',
    '$uibModalInstance',
    'Notification',
    'goal_service',
    'property_view_ids',
    'goal',
    'question_options',
    'write_permission',
    // eslint-disable-next-line func-names
    function (
      $scope,
      $state,
      $uibModalInstance,
      Notification,
      goal_service,
      property_view_ids,
      goal,
      question_options,
      write_permission
    ) {
      $scope.write_permission = write_permission;
      $scope.question_options = question_options;

      $scope.question = { name: 'question', selected: false, value: '' };
      $scope.resolution = { name: 'resolution', selected: false, value: '' };
      $scope.historical_note = { name: 'historical_note', selected: false, value: '' };
      $scope.passed_checks = { name: 'passed_checks', selected: false, value: false };
      $scope.new_or_acquired = { name: 'new_or_acquired', selected: false, value: false };

      const inputs = [$scope.question, $scope.resolution, $scope.historical_note, $scope.passed_checks, $scope.new_or_acquired];
      $scope.save_disabled = () => !inputs.some((input) => input.selected);

      $scope.save = () => {
        const data = {};
        const selected_inputs = inputs.filter((input) => input.selected);
        selected_inputs.forEach((input) => { data[input.name] = input.value; });
        goal_service.bulk_update_goal_note(property_view_ids, goal, data)
          .then((response) => {
            Notification.success(response.data.message);
            $uibModalInstance.close();
          })
          .catch(() => Notification.error('Unexpected Error'))
          .finally(() => $uibModalInstance.close());
      };
      $scope.close = () => {
        $uibModalInstance.dismiss();
      };
    }
  ]);
