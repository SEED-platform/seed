angular.module('BE.docs.controller.faq', [])
  .controller('faq_controller', [
    '$scope',
    '$timeout',
    function ($scope, $timeout) {
      // faq-data must be a script JSON element templated into the page
      const faqScript = angular.element('#faq-data')[0];
      if (!faqScript) {
        console.error('Failed to find FAQ data with id faq-data. Ensure it is inserted before the controller is used.');
      }

      // Autofocus on the input
      angular.element('.faq-search-input')[0].focus();

      $scope.faqData = JSON.parse(faqScript.textContent);

      $scope.updateFilter = search => {
        if (!search) {
          angular.element('.collapse.faq-category-content').collapse('hide');
        } else {
          // Timeout to allow ng-if to evaluate first
          $timeout(function () {
            angular.element('.collapse.faq-category-content').collapse('show');
          }, 0);
        }
      };
    }]);
