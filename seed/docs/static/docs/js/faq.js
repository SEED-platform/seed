angular.module('BE.docs.controller.faq', [])
  .controller('faq_controller', [
    '$scope',
    function($scope) {
      // faq-data must be a script JSON element templated into the page
      const faqScript = document.getElementById('faq-data')
      if (faqScript == undefined) {
        console.error('Failed to find FAQ data with id faq-data. Ensure it is inserted before the controller is used.')
      }

      $scope.faqData = JSON.parse(faqScript.textContent)

      $scope.updateFilter = (search) => {
        if (search == "") {
          $('.collapse.faq-category-content').collapse('hide')
        } else {
          $('.collapse.faq-category-content').collapse('show')
        }
      }
  }])
