/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.controller.api', []).controller('api_controller', [function () {
  $('#swagger-ui').on('load', function () {
    $(this).contents().find('body').css('margin', 0);
  });
}]);
