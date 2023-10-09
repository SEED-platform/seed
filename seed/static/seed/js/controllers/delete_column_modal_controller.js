/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.delete_column_modal', []).controller('delete_column_modal_controller', [
  '$scope',
  '$window',
  '$log',
  '$interval',
  '$uibModalInstance',
  'spinner_utility',
  'columns_service',
  'uploader_service',
  'organization_id',
  'column',
  // eslint-disable-next-line func-names
  function ($scope, $window, $log, $interval, $uibModalInstance, spinner_utility, columns_service, uploader_service, organization_id, column) {
    $scope.column_name = column.column_name;

    $scope.progressBar = {
      progress: 0
    };

    $scope.delete = () => {
      $scope.state = 'pending';
      columns_service
        .delete_column_for_org(organization_id, column.id)
        .then((result) => {
          $scope.state = 'evaluating';
          $scope.interval = $interval(() => {
            $scope.state === 'running' ? $scope.updateTime() : $scope.setRunningState();
          }, 1000);
          $scope.updateTime();
          uploader_service.check_progress_loop(
            result.data.progress_key,
            0,
            1,
            (response) => {
              $scope.result = `${response.message} in ${$scope.elapsed}`;
              $scope.state = 'done';
              $interval.cancel($scope.interval);
            },
            () => {
              // Do nothing
            },
            $scope.progressBar
          );
        })
        .catch((err) => {
          $log.error(err);
          $scope.result = 'Failed to delete column';
          $scope.state = 'done';
          $interval.cancel($scope.interval);
        });
    };

    $scope.elapsedFn = function () {
      const diff = moment().diff(this.startTime);
      return $scope.formatTime(moment.duration(diff));
    };

    $scope.etaFn = function () {
      if ($scope.progressBar.completed_records) {
        if (!$scope.initialCompleted) {
          $scope.initialCompleted = $scope.progressBar.completed_records;
        }
        const diff = moment().diff(this.startTime);
        const progress = ($scope.progressBar.completed_records - $scope.initialCompleted) / ($scope.progressBar.total_records - $scope.initialCompleted);
        if (progress) {
          return $scope.formatTime(moment.duration(diff / progress - diff));
        }
      }
    };

    $scope.setRunningState = function () {
      $scope.eta = $scope.etaFn();
      $scope.eta ? (($scope.state = 'running'), ($scope.startTime = moment())) : null;
    };

    $scope.updateTime = function () {
      $scope.elapsed = $scope.elapsedFn();
      $scope.eta = $scope.etaFn();
    };

    $scope.formatTime = function (duration) {
      const h = Math.floor(duration.asHours());
      const m = duration.minutes();
      const s = duration.seconds();

      if (h > 0) {
        const mPadded = m.toString().padStart(2, '0');
        const sPadded = s.toString().padStart(2, '0');
        return `${h}:${mPadded}:${sPadded}`;
      }
      if (m > 0) {
        const sPadded = s.toString().padStart(2, '0');
        return `${m}:${sPadded}`;
      }
      return `${s}s`;
    };

    $scope.refresh = function () {
      spinner_utility.show();
      $window.location.reload();
    };

    $scope.cancel = function () {
      $uibModalInstance.dismiss();
    };
  }
]);
