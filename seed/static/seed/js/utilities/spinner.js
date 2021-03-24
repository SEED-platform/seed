/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author - Nicholas Serra <nickserra@gmail.com>
 */

/**
 * Eventually this may need to be refactored into a singleton factory that
 * instantiates new objects (spinners). - nicholasserra
 */
angular.module('BE.seed.utility.spinner', []).factory('spinner_utility', [
  function () {

    var spinner_utility = {};
    var _spinner;

    spinner_utility.show = function (params, target) {

      var refresh = !!(params || target);
      target = target || $('.display')[0];

      if (!_spinner) {
        _spinner = new Spinner(params).spin(target);
      } else if (_spinner && refresh) {
        _spinner.stop();
        _spinner = new Spinner(params).spin(target);
      } else {
        _spinner.spin(target);
      }

      $('.page')[0].style.opacity = 0.4;
    };

    spinner_utility.hide = function () {
      if (_spinner) {
        _spinner.stop();
        $('.page')[0].style.opacity = 1;
      }
    };

    return spinner_utility;
  }]);
