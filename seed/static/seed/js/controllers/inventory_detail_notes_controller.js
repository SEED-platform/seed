/**
 * :copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.inventory_detail_notes', [])
  .controller('inventory_detail_notes_controller', [
    '$scope',
    '$window',
    '$uibModalInstance',
    '$stateParams',
    'inventory_service',
    'user_service',
    'note_service',
    '$translate',
    'i18nService', // from ui-grid
    function ($scope, $window, $uibModalInstance, $stateParams, inventory_service, user_service, note_service, $translate, i18nService) {

      $scope.translations = {};

      var needed_translations = [
        'Reset Defaults'
      ];

      $translate(needed_translations).then(function succeeded (translations) {
        $scope.translations = translations;
      }, function failed (translationIds) {
        $scope.translations = translationIds;
      });

      // let angular-translate be in charge ... need
      // to feed the language-only part of its $translate setting into
      // ui-grid's i18nService
      var stripRegion = function (languageTag) {
        return _.first(languageTag.split('_'));
      };
      i18nService.setCurrentLang(stripRegion($translate.proposedLanguage() || $translate.use()));

      // set some defaults and load the notes
      $scope.inventory_type = $stateParams.inventory_type;
      $scope.inventory_id = $stateParams.inventory_id;
      $scope.cycle = $stateParams.cycle_id;
      $scope.org_id = user_service.get_organization().id;

      $scope.notes = note_service.get_notes($scope.org_id, $scope.inventory_type, $scope.inventory_id);
    }]);
