/**
 * :copyright: (c) 2014 Building Energy Inc
 */
angular.module('BE.seed.controller.dataset_detail', [])
.controller('dataset_detail_controller', [
  '$scope',
  'dataset_payload',
  '$log',
  'dataset_service',
  '$uibModal',
  'urls',
  function ($scope, dataset_payload, $log, dataset_service, $uibModal, urls) {
    $scope.dataset = dataset_payload.dataset;

    $log.info('dataset_payload:', dataset_payload);

    $scope.confirm_delete = function (file) {
        var yes = confirm('Are you sure you want to PERMANENTLY delete \'' + file.name + '\'?');
        if (yes) {
            $scope.delete_file(file);
        }
    };
    $scope.delete_file = function(file) {
        dataset_service.delete_file(file.id).then(function(data) {
            // resolve promise
            init();
        });
    };

    /**
     * open_data_upload_modal: opens the data upload modal to step 4, add energy files
     */
    $scope.open_data_upload_modal = function() {
        var dataModalInstance = $uibModal.open({
            templateUrl: urls.static_url + 'seed/partials/data_upload_modal.html',
            controller: 'data_upload_modal_ctrl',
            resolve: {
                step: function(){
                    return 2;
                },
                dataset: function(){
                    return $scope.dataset;
                }
            }
        });

        dataModalInstance.result.then(
            // modal close() function
            function () {
                init();
            // modal dismiss() function
        }, function (message) {
                // dismiss
                init();
        });
    };

    var init = function(){
        dataset_service.get_dataset($scope.dataset.id).then(function(data){
            // resolve promise
            $scope.dataset = data.dataset;
        });
    };

}]);
