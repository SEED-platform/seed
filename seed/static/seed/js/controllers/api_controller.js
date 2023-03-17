/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.controller.api', []).controller('api_controller', [function () {
  $('#swagger-ui').on('load', function () {
    $(this).contents().find('body').css('margin', 0);
  });
}]);
