angular.module('BE.seed.service.simple_modal', [])
.factory('simple_modal_service', [  '$modal',
                                    'urls',
    function ($modal, urls) {

        //TODO : turn these into const when we move to newest js
        var TYPE_ERROR = "error"
        var TYPE_DEFAULT = "default"

        /* Code based on example by Dan Wahlin: http://weblogs.asp.net/dwahlin/building-an-angularjs-modal-service */
        var self = this;

        var modalDefaults = {
            type: TYPE_DEFAULT,            //can be "default" or "error"
            backdrop: 'static',         //user cannot click anywhere on screen to close modal, only buttons
            keyboard: true,             //user can use ESC key to close
            modalFade: true,            
            templateUrl: urls.static_url + 'seed/partials/simple_modal.html'
        };

        var modalOptions = {
            closeButtonText: 'Close',
            actionButtonText: 'OK',
            headerText: 'Proceed?',
            bodyText: 'Perform this action?'
        };

        /*  
            Show a simple modal dialog. Customize the dialog text and behavior by passing in config objects. 

            @param {object} [modalOptions={}]       Optional, but caller really should provide specific button labels and text.
            @param {object} [modalDefaults={}]      Optional, and can have one or more of the properties defined above in this class
        */
        function showModal(customModalOptions, customModalDefaults) {
            if (!customModalDefaults) customModalDefaults = {};
            if (!customModalOptions) customModalOptions = {};
            if (customModalOptions.type != TYPE_DEFAULT && customModalOptions.type != TYPE_ERROR){
                customModalOptions.type != TYPE_DEFAULT;
            }
            show(customModalOptions, customModalDefaults);
        };


        /* Private method. Show Angular UI modal based on config options */        
        var show = function(customModalOptions, customModalDefaults) {
            //Create temp objects to work with since we're in a singleton service
            var tempModalDefaults = {};
            var tempModalOptions = {};

            //Do styling and modifications specific to "errors"
            if (customModalOptions.type == TYPE_ERROR){
                customModalOptions.headerText = "Error: " + customModalOptions.headerText;
            }

            //Map angular-ui modal custom defaults to modal defaults defined in service
            angular.extend(tempModalDefaults, modalDefaults, customModalDefaults);

            //Map modal.html $scope custom properties to defaults defined in service
            angular.extend(tempModalOptions, modalOptions, customModalOptions);

            //If caller doesn't provide controller, build simple one here to handle Ok/Close
            if (!tempModalDefaults.controller) {
                tempModalDefaults.controller = function ($scope, $modalInstance) {
                    $scope.modalOptions = tempModalOptions;
                    $scope.modalOptions.ok = function (result) {
                        $modalInstance.close(result);
                    };
                    $scope.modalOptions.close = function (result) {
                        $modalInstance.dismiss('cancel');
                    };
                }
            }

            return $modal.open(tempModalDefaults).result;
        };


        /* ~~~~~~~~~~ */
        /* Public API */
        /* ~~~~~~~~~~ */
        
        var simple_modal_factory = { 
            
            //properties
            //(none)

            //functions
            showModal : showModal  
        
        };

        return simple_modal_factory;

    }
]);