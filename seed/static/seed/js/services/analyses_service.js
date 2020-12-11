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

      let get_analyses_for_org = function(org_id) {
        return $http.get('/api/v3/analyses/?organization_id=' + org_id).then(function (response) {
          return response.data;
        });
      };

      let get_analyses_for_canonical_property = function(property_id) {
        let org = user_service.get_organization().id;
        return $http.get('/api/v3/analyses/?organization_id=' + org +'&property_id=' + property_id).then(function (response) {
          return response.data;
        });
      };

      let analyses_factory = {
        get_analyses_for_org: get_analyses_for_org,
        get_analyses_for_canonical_property: get_analyses_for_canonical_property
      };

      return analyses_factory;
}]);
