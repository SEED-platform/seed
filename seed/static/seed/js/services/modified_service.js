/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.modified', []).factory('modified_service', [
  '$window',
  '$uibModal',
  'urls',
  function ($window, $uibModal, urls) {
    const modified_service = {};
    let modified = false;

    modified_service.setModified = function () {
      if (!modified) {
        $window.onbeforeunload = _.constant('You have unsaved changes.');
        modified = true;
      }
    };

    modified_service.resetModified = function () {
      if (modified) {
        $window.onbeforeunload = null;
        modified = false;
      }
    };

    modified_service.isModified = () => modified;

    modified_service.showModifiedDialog = function () {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/modified_modal.html`,
        controller: 'modified_modal_controller'
      });

      return modalInstance.result;
    };

    modified_service.showResetDialog = function () {
      const modalInstance = $uibModal.open({
        templateUrl: `${urls.static_url}seed/partials/reset_modal.html`,
        controller: 'reset_modal_controller'
      });

      return modalInstance.result;
    };

    return modified_service;
  }
]);
