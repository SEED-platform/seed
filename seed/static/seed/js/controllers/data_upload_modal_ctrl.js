/**
 * :copyright: (c) 2014 Building Energy Inc
 */
/**
 * data_upload_modal_ctrl: the AngularJS controller for the data upload modal.
 *
 * The numbers corresponding to ``step.number`` are reflected in 
 * modal title changes like so:
 *
 * ng-switch-when="1" == Create a New Data Set.
 * ng-switch-when="2" == Upload your building list.
 * ng-switch-when="3" == Successful upload!
 * ng-switch-when="4" == Upload your energy data.
 * ng-switch-when="5" == Successful upload!
 * ng-switch-when="6" == What type of .csv file would you like to upload?
 * ng-switch-when="7" == Finding building matches.
 * ng-switch-when="8" == 450 building matches found.
 * ng-switch-when="8" == Add files to your Data Set.
 * ng-switch-when="9" == Add files to {$ dataset.name $}
 * ng-switch-when="10" == No matches found
 */
angular.module('BE.seed.controller.data_upload_modal', [])
.controller('data_upload_modal_ctrl', [
  '$scope',
  '$modalInstance',
  'step',
  'dataset',
  '$timeout',
  'uploader_service',
  '$location',
  'mapping_service',
  'matching_service',
  'building_services',
  function (
    $scope,
    $modalInstance,
    step,
    dataset,
    $timeout,
    uploader_service,
    $location,
    mapping_service,
    matching_service,
    building_services
    ) {
    $scope.step_10_style = "info";
    $scope.step_10_title = "load more data";
    $scope.step = {
        number: step
    };
    /**
     * dataset: holds the state of the data set
     * name: string - the data set name
     * disabled: return bool - when true: disables the `Create Data Set` button
     * alert: bool - when true: shows the bootstrap alert `the file name is 
     *  already in use`
     * id: int - set with `create_dataset` resolve promise, is the id of the 
     *  newly created data set
     * file: the file being upload file.filename is the file's name
     */
    $scope.dataset = {
        name: "",
        disabled: function() {
            var name = $scope.dataset.name || "";
            if (name.length === 0) {
                return true;
            }
            return false;
        },
        alert: false,
        id: 0,
        filename: "",
        import_file_id: 0
    };
    /**
     * uploader: hold the state of the upload. 
     * invalid_extension_alert: bool - hides or shows the bootstrap alert
     * in_progress: bool - when true: shows the progress bar and hides the 
     *  upload button. when false: hides the progress bar and shows the upload
     *  button.
     * progress: int or float - the progress bar value, i.e. percentage complete
     * complete: bool - true when the upload has finished
     */
    $scope.uploader = {
        invalid_extension_alert: false,
        in_progress: false,
        progress: 0,
        complete: false,
        status_message: ""
    };

    /**
     * goto_step: changes the step of the modal, i.e. name dataset -> upload ...
     * step: int - used with the `ng-switch` in the DOM to change state
     * step_text: 
     */
    $scope.goto_step = function (step) {
        $scope.step.number = step;
        check_suppress_click();
    };
    /**
     * close: closes the modal, routes to the close function of the parent scope
     */
    $scope.close = function () {
        $modalInstance.close();
    };
    $scope.goto_data_mapping = function () {
        $modalInstance.close();
        $location.path('/data/mapping/' + $scope.dataset.import_file_id);
    };
    $scope.goto_data_matching = function () {
        $modalInstance.close();
        $location.path('/data/matching/' + $scope.dataset.import_file_id);
    };
    $scope.view_my_buildings = function () {
        $modalInstance.close();
        $location.path('/buildings/');
    };
    /**
     * cancel: dismissed the modal, routes to the dismiss function of the parent
     *  scope
     */
    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };
    /**
     * create_dataset: uses the `uploader_service` to create a new data set. If
     *  there is an error, i.e. the request fails or the data set name is
     *  already taken, then the bootstrap alert is shown
     */
    $scope.create_dataset = function(dataset_name) {
        uploader_service.create_dataset(dataset_name).then(
            function(data) {
                // resolve promise
                $scope.goto_step(2);
                $scope.dataset.id = data.id;
                $scope.dataset.name = data.name;
                $scope.uploader.status_message = "uploading file";
            },
            function(status, error) {
                // reject promise
                var message = status.message || "";
                if (message === "name already in use"){
                    $scope.dataset.alert = true;
                }
            }
        );
    };
    /**
     * uploaderfunc: the callback function passed to beUploader. Depending on 
     *  the `event_message` from beUploader, it will change the state of the 
     *  modal, show the `invalid_extension` alert, and update the progress bar.
     */
    $scope.uploaderfunc = function(event_message, file, progress) {
        if (event_message === "invalid_extension") {
            $scope.uploader.invalid_extension_alert = true;
        }
        if (event_message === "upload_submitted") {
            $scope.dataset.filename = file.filename;
            $scope.uploader.in_progress = true;
            $scope.uploader.status_message = "uploading file";
        }
        if (event_message === "upload_complete") {
            var current_step = $scope.step.number;
            var data_is_green_button = 
          
            $scope.uploader.status_message = "upload complete";
            $scope.dataset.import_file_id = file.file_id;
            // Assessed Data
            if (current_step === 2) {
                var is_green_button = (file.source_type === "Green Button Raw");
                save_raw_assessed_data(file.file_id, is_green_button);
            }
            // Portfolio Data
            if (current_step === 4) {
                save_map_match_PM_data(file.file_id);
            }
            
        }
        if (event_message === "upload_in_progress") {
            $scope.uploader.in_progress = true;
            $scope.uploader.progress = 25.0 * progress.loaded / progress.total;
        }
        // $apply() or $digest() needed maybe because of this:
        // https://github.com/angular-ui/bootstrap/issues/1798
        // otherwise alert doesn't show unless modal is interacted with
        if (!$scope.$$phase) {
            $scope.$apply();
        }
    };

    /**
     * save_map_match_PM_data: saves, maps, and matches PM data
     *
     * @param {string} file_id: the id of the import file
     */
    var save_map_match_PM_data = function (file_id) {
        $scope.uploader.status_message = "saving energy data";
        $scope.uploader.progress = 25;
        uploader_service.save_raw_data(file_id)
        .then(function(data) {
            // resolve save_raw_data promise
            monitor_save_raw_data(data.progress_key, file_id);
        });
    };

    /**
     * monitor_save_raw_data: updates progress bar from 25% to 50%,
     *   called by save_map_match_PM_data
     *
     * @param {string} progress_key: key
     * @param {string} file_id: id of file
     */
    var monitor_save_raw_data = function(progress_key, file_id) {
        uploader_service.check_progress_loop(progress_key, 25, 0.25, function(data){
            $scope.uploader.status_message = "auto-mapping energy data";
            mapping_service.start_mapping(file_id).then(function (dataa){
                monitor_mapping(dataa.progress_key, file_id);
            });
        }, $scope.uploader);
    };

    /**
     * monitor_mapping: called by monitor_save_raw_data, updates progress bar
     *   from 50% to 75%
     *
     * @param {string} progress_key: key
     * @param {string} file_id: id of file
     */
    var monitor_mapping = function(progress_key, file_id) {
        uploader_service.check_progress_loop(progress_key, 50, 0.25, function(data){
            $scope.uploader.status_message = "auto-matching energy data";
            matching_service.start_system_matching(file_id).then(function (dataa){
                monitor_matching(dataa.progress_key, file_id);
            });
        }, $scope.uploader);
    };

    /**
     * monitor_matching: called by monitor_mapping, updates progress bar
     *   from 75% to 100%, then shows the PM upload completed
     *
     * @param {string} progress_key: key
     * @param {string} file_id: id of file
     */
    var monitor_matching = function(progress_key, file_id) {
        uploader_service.check_progress_loop(progress_key, 75, 0.25, function(data){                
            $scope.uploader.complete = true;
            $scope.uploader.in_progress = false;
            $scope.uploader.progress = 1;
            $scope.step.number = 5;
        }, $scope.uploader);
    };

    /**
     * save_raw_assessed_data: saves Assessed data
     *
     * @param {string} file_id: the id of the import file
     */
    var save_raw_assessed_data = function (file_id, is_green_button) {
        $scope.uploader.status_message = "saving data";
        $scope.uploader.progress = 45;
        uploader_service.save_raw_data(file_id)
        .then(function(data){
            uploader_service.check_progress_loop(data.progress_key, 45, 0.55, function(data){
                $scope.uploader.status_message = "saving complete";
                $scope.uploader.progress = 100;
                
                if (is_green_button) {
                    $scope.step.number = 8;
                } else {
                    $scope.step.number = 3;
                }

            }, $scope.uploader);
        });
    };

    /**
     * find_matches: finds matches for buildings within an import file
     */
    $scope.find_matches = function() {
        var import_file_id = $scope.dataset.import_file_id;
        matching_service.start_system_matching(
            import_file_id
        ).then(function (data){
            if (data.status === "error" || data.status === "warning") {
                $scope.uploader.complete = true;
                $scope.uploader.in_progress = false;
                $scope.uploader.progress = 0;
                $scope.step.number = 10;
                $scope.step_10_style = "danger";
                $scope.step_10_error_message = data.message;
                $scope.step_10_title = data.message;
            } else {
                uploader_service.check_progress_loop(
                    data.progress_key,
                    0,
                    1.0,
                    function (data){
                        building_services.get_PM_filter_by_counts($scope.dataset.import_file_id)
                        .then(function (data){
                            // resolve promise
                            $scope.matched_buildings = data.matched;
                            $scope.unmatched_buildings = data.unmatched;
                            $scope.uploader.complete = true;
                            $scope.uploader.in_progress = false;
                            $scope.uploader.progress = 0;
                            if ($scope.matched_buildings > 0) {
                                $scope.step.number = 8;
                            } else {
                                $scope.step.number = 10;
                            }
                        });
                    },
                    $scope.uploader
                );
            }
        });
    };

    var check_suppress_click = function() {
        if($scope.step.number === 2) {
            angular.element('.modal').off('click');
        }
    };

    /**
     * init: ran upon the controller load
     */
    var init = function() {
        angular.extend($scope.dataset, dataset);
        // set the `Data Set Name` input textbox to have key focus.
        $scope.step = {
            number: step
        };
        // goto matching progress
        if ($scope.step.number === 7){
            $scope.find_matches();
        }
        $timeout(function(name) {
            angular.element('#inputDataUploadName').focus();

            //suppress the dismissing of the data upload modal when the background is clicked
            //the default dismiss leads to confusion about whether the upload was canceled - megha 1/22
            check_suppress_click();   

        }, 50);
    };
    init();

}]);
