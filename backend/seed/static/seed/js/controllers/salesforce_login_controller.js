/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.salesforce_login', []).controller('salesforce_login_controller', [
  '$scope',
  '$state',
  '$window',
  'bb_salesforce_service',
  'organization_id',
  // eslint-disable-next-line func-names
  function (
    $scope,
    $state,
    $window,
    bb_salesforce_service,
    organization_id
  ) {
    $scope.organization_id = organization_id;
    $scope.write_permission = ($scope.menu.user.is_ali_root || !$scope.menu.user.is_ali_leaf) && !$scope.viewer;
    $scope.AUTHENTICATION_STATE = 'PENDING'; // PENDING, FAILURE, SUCCESS
    $scope.error_message = null;
    // get code from browser URL (code gets put in the middle of the URL by salesforce)
    const params = new URLSearchParams($window.location.search);
    const code = params.get('code');
    bb_salesforce_service.get_token(code, organization_id).then((data) => {
      if (data.status === 'success') {
        $scope.AUTHENTICATION_STATE = 'SUCCESS';
      } else {
        $scope.AUTHENTICATION_STATE = 'FAILURE';
        $scope.error_message = data.response;
      }
    });

    $scope.login_salesforce = () => {
      bb_salesforce_service.get_login_url(organization_id).then((data) => {
        $window.location.href = data.url;
      });
    };
  }
]);
