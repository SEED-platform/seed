/*
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.cycle_admin', [])
  .controller('cycle_admin_controller', [
    '$scope',
    '$log',
    'urls',
    'Notification',
    'cycle_service',
    'cycles_payload',
    'organization_payload',
    'auth_payload',
    '$translate',
    '$sce',
    '$uibModal',
    function ($scope, $log, urls, Notification, cycle_service, cycles_payload, organization_payload, auth_payload, $translate, $sce, $uibModal) {

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

      function translateMessage (msg, params) {
        // TODO XSS, discuss with Nick and Alex
        return $sce.getTrustedHtml($translate.instant(msg, params));
      }

      /*  Take user input from New Cycle form and submit
       to service to create a new cycle. */
      $scope.submitNewCycleForm = function (form) {
        if (form.$invalid) {
          return;
        }
        cycle_service.create_cycle_for_org($scope.new_cycle, $scope.org.id).then(function () {
          var msg = translateMessage('CREATED_NEW_CYCLE', {
            cycle_name: getTruncatedName($scope.new_cycle.name)
          });
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
          var msg = translateMessage('Cycle updated.');
          Notification.primary(msg);
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        }, function (message) {
          $log.error('Error saving cycle.', message);
        });
      };

      $scope.opened = {};
      $scope.open = function ($event, elementOpened) {
        $event.preventDefault();
        $event.stopPropagation();

        if (elementOpened === 'end') $scope.opened.start = false;
        if (elementOpened === 'start') $scope.opened.end = false;
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

      $scope.showDeleteCycleModal = function (cycle_id) {
        const delete_cycle_modal = $uibModal.open({
          templateUrl: urls.static_url + 'seed/partials/delete_cycle_modal.html',
          controller: 'delete_cycle_modal_controller',
          backdrop: 'static',
          keyboard: false,
          resolve: {
            // use cycle data from organization endpoint b/c it includes inventory counts
            cycle: (organization_service) => {
              return organization_service.get_organization($scope.org.id)
                .then(res => {
                  return res.organization.cycles.find(cycle => cycle.cycle_id == cycle_id)
                })
            },
            organization_id: () => $scope.org.id
          }
        });
        delete_cycle_modal.result.then(function () {
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        }).catch(function () {
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        });
      };
    }
  ]);
