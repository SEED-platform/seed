/*
 * :copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.utility.spinner', []).service('spinner_utility', [
  function () {

    var spinner_utility = {spinner : null};

    spinner_utility.show = function(params, target) {
      var target = target || $('.display')[0]
      spinner_utility.spinner = new Spinner(params).spin(target);
      $('.page')[0].style.opacity = 0.4;
    };

    spinner_utility.hide = function() {
      spinner_utility.spinner.stop();
      $('.page')[0].style.opacity = 1;
    };

    return spinner_utility;
}]);
