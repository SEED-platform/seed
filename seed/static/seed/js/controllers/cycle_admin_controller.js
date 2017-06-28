/*
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.cycle_admin', [])
  .controller('cycle_admin_controller', [
    '$scope',
    '$log',
    'urls',
    'simple_modal_service',
    'Notification',
    'cycle_service',
    'cycles_payload',
    'organization_payload',
    'auth_payload',
    function ($scope, $log, urls, simple_modal_service, Notification, cycle_service, cycles_payload, organization_payload, auth_payload) {

      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
      var processCycles = function (cycles) {
        $scope.cycles = _.map(cycles.cycles, function (cycle) {
          cycle.start = new Date(cycle.start);
          cycle.end = new Date(cycle.end);
          return cycle;
        });
      };
      processCycles(cycles_payload);

      function initialize_new_cycle () {
        $scope.new_cycle = {start: null, end: null, name: ''};
      }

      /*  Take user input from New Cycle form and submit
       to service to create a new cycle. */
      $scope.submitNewCycleForm = function (form) {
        if (form.$invalid) {
          return;
        }
        cycle_service.create_cycle_for_org($scope.new_cycle, $scope.org.id).then(function () {
          var msg = 'Created new Cycle ' + getTruncatedName($scope.new_cycle.name);
          Notification.primary(msg);
          initialize_new_cycle();
          form.$setPristine();
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        }, function (message) {
          $log.error('Error creating new cycle.', message);
        }
        );
      };


      /* Checks for existing cycle name for inline edit form.
       Form assumes function will return a string if there's an existing cycle */
      $scope.checkEditCycleBeforeSave = function (newCycleName, currentCycleName) {
        if (newCycleName === currentCycleName) return;
        if (_.isEmpty(newCycleName)) return 'Enter at least one character';
        if (isCycleNameUsed(newCycleName)) return 'That Cycle name already exists';
      };

      function isCycleNameUsed (newCycleName) {
        return _.some($scope.cycles, function (obj) {
          return obj.name === newCycleName;
        });
      }

      /* Submit edit when 'enter' is pressed */
      $scope.onEditCycleNameKeypress = function (e, form) {
        if (e.which === 13) {
          form.$submit();
        }
      };


      $scope.saveCycle = function (cycle, id) {
        //Don't update $scope.cycle until a 'success' from server
        angular.extend(cycle, {id: id});
        cycle_service.update_cycle_for_org(cycle, $scope.org.id).then(function () {
          var msg = 'Cycle updated.';
          Notification.primary(msg);
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        }, function (message) {
          $log.error('Error saving cycle.', message);
        });
      };

      //commented out 6.15.17 ability to delete cycle is commented out dbressan code cov work
      // $scope.deleteCycle = function (cycle) {
      //   cycle_service.delete_cycle_for_org(cycle, $scope.org.id).then(function () {
      //     var msg = 'Cycle deleted.';
      //     Notification.primary(msg);
      //     cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
      //   }, function (message) {
      //     $log.error('Error deleting cycle.', message);
      //   });
      // };

      $scope.opened = {};
      $scope.open = function ($event, elementOpened) {
        $event.preventDefault();
        $event.stopPropagation();

        if (elementOpened == 'end') $scope.opened.start = false;
        if (elementOpened == 'start') $scope.opened.end = false;
        $scope.opened[elementOpened] = !$scope.opened[elementOpened];
      };

      // Datepickers
      $scope.startDatePickerOpen = false;
      $scope.endDatePickerOpen = false;
      $scope.invalidDates = false; // set this to true when startDate >= endDate;


      // Handle datepicker open/close events
      $scope.openStartDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.startDatePickerOpen = !$scope.startDatePickerOpen;
      };
      $scope.openEndDatePicker = function ($event) {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.endDatePickerOpen = !$scope.endDatePickerOpen;
      };

      $scope.$watch('startDate', function () {
        $scope.checkInvalidDate();
      });

      $scope.$watch('endDate', function ( ) {
        $scope.checkInvalidDate();
      });

      $scope.checkInvalidDate = function () {
        $scope.invalidDates = ($scope.endDate < $scope.startDate);
      };

      function getTruncatedName (name) {
        if (name && name.length > 20) {
          name = name.substr(0, 20) + '...';
        }
        return name;
      }

      initialize_new_cycle();

    }
  ]);
