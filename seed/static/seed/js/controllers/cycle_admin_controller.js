/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */

angular.module('BE.seed.controller.cycle_admin', [])
.controller('cycle_admin_controller', [
    '$scope',
    '$log',
    'urls',
    'cycle_service',
    'simple_modal_service',
    'Notification',
function ($scope, $log, urls, cycle_service, simple_modal_service, notification) {

    $scope.cycles = [];

    function initialize_new_cycle() {
        $scope.new_cycle = { from_date:'', to_date:'', name:'' };
    }

    /*  Take user input from New Cycle form and submit
        to service to create a new cycle. */
    $scope.submitNewCycleForm = function (form){
        if (form.$invalid) {
            return;
        }
        cycle_service.create_cycle($scope.new_cycle).then(
            function(result){
                get_cycles();
                var msg = 'Created new Cycle ' + getTruncatedName($scope.new_cycle.name);
                notification.primary(msg);
                initialize_new_cycle();
                form.$setPristine();
            },
            function(message){
                $log.error('Error creating new cycle.', message);
            }
        );
    };


    /* Checks for existing cycle name for inline edit form.
        Form assumes function will return a string if there's an existing cycle */
    $scope.checkEditCycleBeforeSave = function(data, currentCycleName){
        if (data === currentCycleName){
            return;
        }
        if (data===undefined || data==='') {
            return 'Enter at least one character';
        }
        if(isCycleNameUsed(data)){
            return 'That Cycle name already exists';
        }
    };

    function isCycleNameUsed(newCycleName) {
				return _.some($scope.cycles, function(obj){
						return obj.name === newCycleName;
				});
    }

    /* Submit edit when 'enter' is pressed */
    $scope.onEditCycleNameKeypress = function(e, form) {
        if (e.which === 13) {
            form.$submit();
        }
    };



    $scope.saveCycle = function(cycle, id, index) {
        //Don't update $scope.cycle until a 'success' from server
        angular.extend(cycle, {id: id});
        cycle_service.update_cycle(cycle).then(
            function(data){
                var msg = 'Cycle updated.';
                notification.primary(msg);
                $scope.cycles.splice(index, 1, data);
                $scope.cycle = data;
            },
            function(message){
                $log.error('Error saving cycle.', message);
            }
        );
    };

		/* A delete operation has lots of consequences that are not completely
		   defined. Not implementing at the moment.

    $scope.deleteCycle = function(cycle, index) {
        var modalOptions = {
            type: 'default',
            okButtonText: 'OK',
            cancelButtonText: 'Cancel',
            headerText: 'Confirm delete',
            bodyText: 'Delete cycle "' + cycle.name + '"?'
        };
        simple_modal_service.showModal(modalOptions).then(
            function(result){
                //user confirmed delete, so go ahead and do it.
                cycle_service.delete_cycle(cycle).then(
                    function(result){
                        //server deleted cycle, so remove it locally
                        $scope.cycles.splice(index, 1);
                        var msg = 'Deleted cycle ' + getTruncatedName(cycle.name);
                        notification.primary(msg);
                    },
                    function(message){
                        $log.error('Error deleting cycle.', message);
                    }
                );
            },
            function(message){
                //user doesn't want to delete after all.
        });

    };
	 */


   function get_cycles(cycle) {
        // gets all cycles for an org user
        cycle_service.get_cycles().then(function(data) {
            // resolve promise
            $scope.cycles = data.results;
        });
    }

    function getTruncatedName(name) {
        if (name && name.length>20){
             name = name.substr(0, 20) + '...';
        }
        return name;
    }

    function init(){
       get_cycles();
       initialize_new_cycle();
    }
    init();

}
]);
