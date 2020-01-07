/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
/**
    This service provides a simple, standardized way to show a basic modal dialog.
    Code based on example by Dan Wahlin:
    http://weblogs.asp.net/dwahlin/building-an-angularjs-modal-service

    You can call this service's main method "showModal()" and pass in a modalOptions
    object with the title and message you want to show. You don't have to provide
    this object but the defaults probably won't be helpful to your user, so
    it's best to pass in an object  with appropriate messages.

    The modalOptions object can have the following properties:

        okButtonText        Text for the "ok" or action button. Use this button if
                            there's only one button on the modal.
        cancelButtonText    Text for the cancel button, use null to hide this button
        headerText          Text for the modal header
        bodyText            Text for the modal body
        okResult            Message to be passed back if user clicks okButton

    Your controller method should handle ok and cancel (error) events via the
    promise returned from showModal().

    You can also pass in an optional "modalDefaults" object if you want to
    change how the modal behaves.

    Again, this service is only for simple modals. More complex modal windows should be
    created as a separate service.

*/
angular.module('BE.seed.service.simple_modal', [])
  .factory('simple_modal_service', ['$uibModal',
    'urls',
    function ($uibModal, urls) {

      // Define types of modals allowed.
      // TODO:    Create more configurations for different types of modals, e.g. standard, error
      //          Adding each new type to the validModalTypes array
      // TODO :   turn vars into const when we move to ES6
      var TYPE_DEFAULT = 'default';
      var TYPE_ERROR = 'error';
      var validModalTypes = [TYPE_DEFAULT, TYPE_ERROR];

      var modalDefaults = {
        type: TYPE_DEFAULT, //can be "default" or "error"
        backdrop: 'static', //user cannot click anywhere on screen to close modal, only buttons
        keyboard: true, //user can use ESC key to close
        modalFade: true,
        templateUrl: urls.static_url + 'seed/partials/simple_modal.html'
      };

      var modalOptions = {
        okButtonText: 'Ok',
        cancelButtonText: 'Cancel',
        headerText: 'Proceed?',
        bodyText: 'Perform this action?',
        okResult: 'Ok'
      };

      /**
       Show a simple modal dialog. Customize the dialog text and behavior by passing in config objects.

       @param {object} [modalOptions={}]       Optional, but caller really should provide specific button labels and text.
       @param {object} [modalDefaults={}]      Optional, and can have one or more of the properties defined above in this class
       */
      function showModal (customModalOptions, customModalDefaults) {
        if (customModalOptions && customModalOptions.type !== null) {
          if (!_.includes(validModalTypes, customModalOptions.type)) {
            throw 'Invalid modal type';
          }
        }

        if (!customModalDefaults) customModalDefaults = {};
        if (!customModalOptions) customModalOptions = {};

        return show(customModalOptions, customModalDefaults);
      }


      /* Private method. Show Angular UI modal based on config options */
      var show = function (customModalOptions, customModalDefaults) {
        //Create temp objects to work with since we're in a singleton service
        var tempModalDefaults = {};
        var tempModalOptions = {};

        //Do styling and modifications specific to "errors"
        if (customModalOptions.type === TYPE_ERROR) {
          customModalOptions.headerText = 'Error: ' + customModalOptions.headerText;
        }

        //Map angular-ui modal custom defaults to modal defaults defined in service
        angular.extend(tempModalDefaults, modalDefaults, customModalDefaults);

        //Map modal.html $scope custom properties to defaults defined in service
        angular.extend(tempModalOptions, modalOptions, customModalOptions);

        tempModalDefaults.controller = function ($scope, $uibModalInstance) {
          $scope.modalOptions = tempModalOptions;
          $scope.modalOptions.ok = function () {
            $uibModalInstance.close(tempModalOptions.okResult);
          };
          $scope.modalOptions.cancel = function () {
            $uibModalInstance.dismiss('cancel');
          };
        };

        return $uibModal.open(tempModalDefaults).result;
      };


      /* ~~~~~~~~~~ */
      /* Public API */
      /* ~~~~~~~~~~ */

      var simple_modal_factory = {

        //properties
        //(none)

        //functions
        showModal: showModal

      };

      return simple_modal_factory;

    }
  ]);
