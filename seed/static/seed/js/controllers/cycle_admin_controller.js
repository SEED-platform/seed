/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.cycle_admin', [])
  .controller('cycle_admin_controller', [
    '$scope',
    '$filter',
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
    function ($scope, $filter, $log, urls, Notification, cycle_service, cycles_payload, organization_payload, auth_payload, $translate, $sce, $uibModal) {
      $scope.org = organization_payload.organization;
      $scope.auth = auth_payload.auth;
      const processCycles = (cycles) => {
        $scope.cycles = _.map(cycles.cycles, (cycle) => {
          // Force 'YYYY-MM-DD' date parsing to use the local timezone by parsing as 'YYYY/MM/DD'
          cycle.start = new Date(cycle.start.replace(/-/g, '/'));
          cycle.end = new Date(cycle.end.replace(/-/g, '/'));
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

      // Take user input from New Cycle form and submit to service to create a new cycle.
      $scope.submitNewCycleForm = (form) => {
        if (form.$invalid) {
          return;
        }
        // The datepicker component returns date objects with timezones
        // ex: Mon Jan 01 2018 00:00:00 GMT-0700 (Mountain Standard Time)
        // Cycle model requires YYYY-MM-DD without time or timezone
        $scope.new_cycle.start = $scope.format_date($scope.new_cycle.start);
        $scope.new_cycle.end = $scope.format_date($scope.new_cycle.end);
        cycle_service.create_cycle_for_org($scope.new_cycle, $scope.org.id).then(() => {
          const msg = translateMessage('CREATED_NEW_CYCLE', {
            cycle_name: getTruncatedName($scope.new_cycle.name)
          });
          Notification.primary(msg);
          initialize_new_cycle();
          form.$setPristine();
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        }, (message) => {
          $log.error('Error creating new cycle.', message);
        });
      };

      $scope.format_date = (date) => $filter('date')(date, 'yyyy-MM-dd');

      /* Checks for existing cycle name for inline edit form.
       Form assumes function will return a string if there's an existing cycle */
      $scope.checkEditCycleBeforeSave = (newCycleName, currentCycleName) => {
        if (newCycleName === currentCycleName) return;
        if (_.isEmpty(newCycleName)) return 'Enter at least one character';
        if (isCycleNameUsed(newCycleName)) return 'That Cycle name already exists';
      };

      $scope.checkEditCycleDateBeforeSave = (form, updatedDate) => {
        if (updatedDate === undefined) {
          return 'Invalid date';
        }

        const {start, end} = form.$data;
        if (end < start) {
          return '\'From Date\' must be before \'To Date\'';
        }
      };

      function isCycleNameUsed (newCycleName) {
        return $scope.cycles.some(({name}) => name === newCycleName);
      }

      /* Submit edit when 'enter' is pressed */
      $scope.onEditCycleNameKeypress = (e, form) => {
        if (e.which === 13) {
          form.$submit();
        }
      };


      $scope.saveCycle = (cycle, id) => {
        //Don't update $scope.cycle until a 'success' from server
        cycle = {
          id,
          name: cycle.name,
          start: $scope.format_date(cycle.start),
          end: $scope.format_date(cycle.end)
        };
        cycle_service.update_cycle_for_org(cycle, $scope.org.id).then(() => {
          const msg = translateMessage('Cycle updated.');
          Notification.primary(msg);
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        }, (message) => {
          $log.error('Error saving cycle.', message);
        });
      };

      $scope.opened = {};
      $scope.open = ($event, elementOpened) => {
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
      $scope.openStartDatePicker = ($event) => {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.startDatePickerOpen = !$scope.startDatePickerOpen;
      };
      $scope.openEndDatePicker = ($event) => {
        $event.preventDefault();
        $event.stopPropagation();
        $scope.endDatePickerOpen = !$scope.endDatePickerOpen;
      };

      $scope.$watch('new_cycle.start', () => {
        $scope.checkInvalidDate();
      });

      $scope.$watch('new_cycle.end', () => {
        $scope.checkInvalidDate();
      });

      $scope.checkInvalidDate = () => {
        const {start, end} = $scope.new_cycle;
        $scope.invalidDates = (start === undefined) || (end === undefined) || ($scope.new_cycle.end < $scope.new_cycle.start);
      };

      function getTruncatedName (name) {
        if (name && name.length > 20) {
          name = `${name.slice(0, 20)}…`;
        }
        return name;
      }

      initialize_new_cycle();

      $scope.showDeleteCycleModal = (cycle_id) => {
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
                  return res.organization.cycles.find(cycle => cycle.cycle_id === cycle_id);
                });
            },
            organization_id: () => $scope.org.id
          }
        });
        delete_cycle_modal.result.then(() => {
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        }).catch(() => {
          cycle_service.get_cycles_for_org($scope.org.id).then(processCycles);
        });
      };
    }
  ]);
