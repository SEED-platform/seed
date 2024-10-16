/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.confirm_organization_deletion_modal', []).controller('confirm_organization_deletion_modal_controller', [
  '$scope',
  '$state',
  '$uibModalInstance',
  'org',
  'organization_service',
  '$interval',
  'uploader_service',
  '$window',
  '$log',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $uibModalInstance,
    org,
    organization_service,
    $interval,
    uploader_service,
    $window,
    $log
  ) {
    $scope.org = org;
    $scope.step = {
      number: 1
    };

    $scope.progressBar = {
      progress: 0
    };

    $scope.goto_step = (step) => {
      $scope.step.number = step;
    };


    $scope.confirm_and_delete_org = () => {
      $scope.state = 'pending';
      organization_service.delete_organization(org.org_id)
        .then((result) => {
          $scope.state = 'evaluating';
          $scope.interval = $interval(() => {
            if ($scope.state === 'running') {
              $scope.updateTime();
            } else {
              $scope.setRunningState();
            }
          }, 1000);
          $scope.updateTime();
          uploader_service.check_progress_loop(
            result.progress_key,
            0,
            1,
            (response) => {
              $scope.result = `Completed in ${$scope.elapsed}`;
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
          $scope.result = 'Failed to remove organiazation';
          $scope.state = 'done';
          $interval.cancel($scope.interval);
        });
    };

    $scope.cancel = () => {
      $uibModalInstance.dismiss();
    };

    $scope.elapsedFn = () => {
      const diff = moment().diff($scope.startTime);
      return $scope.formatTime(moment.duration(diff));
    };

    $scope.etaFn = () => {
      if ($scope.progressBar.completed_records) {
        if (!$scope.initialCompleted) {
          $scope.initialCompleted = $scope.progressBar.completed_records;
        }
        const diff = moment().diff($scope.startTime);
        const progress = ($scope.progressBar.completed_records - $scope.initialCompleted) / ($scope.progressBar.total_records - $scope.initialCompleted);
        if (progress) {
          return $scope.formatTime(moment.duration(diff / progress - diff));
        }
      }
    };

    $scope.setRunningState = () => {
      $scope.eta = $scope.etaFn();
      if ($scope.eta) {
        $scope.state = 'running';
        $scope.startTime = moment();
      }
    };

    $scope.updateTime = () => {
      $scope.elapsed = $scope.elapsedFn();
      $scope.eta = $scope.etaFn();
    };

    $scope.formatTime = (duration) => {
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

    $scope.refresh = () => {
      $window.onbeforeunload = null;
      $window.location.reload();
    };

    $scope.org_name = () => {
      return $scope.org.name;
    }
  }

]);
