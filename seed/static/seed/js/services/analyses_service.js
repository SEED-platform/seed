angular.module('BE.seed.service.analyses', [])
  .factory('analyses_service', [
    '$http',
    '$log',
    'user_service',
    function (
      $http,
      $log,
      user_service
    ) {

      let get_labels = function() {
        return get_analyses_for_org(user_service.get_organization().id);
      };

      let get_analyses_for_org = function(org_id) {
        return $http.get('/api/v3/analyses/?organization_id=' + org_id).then(function (response) {
          return response.data;
        });
      };

      let analyses_factory = {
        get_analyses_for_org: get_analyses_for_org
      };

      return analyses_factory;
}]);
