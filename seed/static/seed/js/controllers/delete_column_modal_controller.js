/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.delete_column_modal', [])
  .controller('delete_column_modal_controller', [
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
    function ($scope, $window, $log, $interval, $uibModalInstance, spinner_utility, columns_service, uploader_service, organization_id, column) {
      $scope.column_name = column.column_name;

      $scope.progressBar = {
        progress: 0
      };

      $scope.delete = function () {
        $scope.state = 'pending';
        columns_service.delete_column_for_org(organization_id, column.id).then(function (result) {
          $scope.state = 'running';
          $scope.startTime = moment();
          $scope.interval = $interval(function () {
            $scope.updateTime();
          }, 1000);
          $scope.updateTime();
          uploader_service.check_progress_loop(result.data.progress_key, 0, 1, function (response) {
            $scope.result = response.message + ' in ' + $scope.elapsed;
            $scope.state = 'done';
            $interval.cancel($scope.interval);
          }, function () {
            // Do nothing
          }, $scope.progressBar);
        }).catch(function (err) {
          $log.error(err);
          $scope.result = 'Failed to delete column';
          $scope.state = 'done';
          $interval.cancel($scope.interval);
        });
      };

      $scope.elapsedFn = function () {
        var diff = moment().diff(this.startTime);
        return $scope.formatTime(moment.duration(diff));
      };

      $scope.etaFn = function () {
        if ($scope.progressBar.completed_records) {
          if (!$scope.initialCompleted) {
            $scope.initialCompleted = $scope.progressBar.completed_records;
          }
          var diff = moment().diff(this.startTime);
          var progress = ($scope.progressBar.completed_records - $scope.initialCompleted) / ($scope.progressBar.total_records - $scope.initialCompleted);
          if (progress) {
            return $scope.formatTime(moment.duration(diff / progress - diff));
          }
        }
      };

      $scope.updateTime = function () {
        $scope.elapsed = $scope.elapsedFn();
        $scope.eta = $scope.etaFn();
      };

      $scope.formatTime = function (duration) {
        var h = Math.floor(duration.asHours());
        var m = duration.minutes();
        var s = duration.seconds();

        if (h > 0) {
          var mPadded = m.toString().padStart(2, '0');
          var sPadded = s.toString().padStart(2, '0');
          return `${h}:${mPadded}:${sPadded}`;
        } else if (m > 0) {
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
    }]);
