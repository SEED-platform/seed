angular.module('BE.seed.service.cycle',
    []).factory('cycle_service', ['$http',
                                    '$q',
                                    '$timeout',
                                    '$log',
                                    'user_service',
                        function (  $http,
                                    $q,
                                    $timeout,
                                    $log,
                                    user_service
                                    ) {


    /** Cycle Service:
        --------------------------------------------------
        Provides methods to add/edit cycles on the server.
    */


    /** Returns an array of cycles.

        Returned cycle objects should have the following properties,
        with 'text' and 'color' properties assigned locally.

            id {integer}            The id of the Cycle.
            name {string}           The text that appears in the Cycle.
            start_date {string}     Start date for Cycle.
            end_date {string}       End date for Cycle.

    */

    function get_cycles() {
        var defer = $q.defer();

        var searchArgs = {
            organization_id: user_service.get_organization().id
        };

        $http({
            method: 'GET',
            url: '/app/cycles/',
            params: searchArgs
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /*  Add a cycle to an organization's list of cycles

        @param {object} cycle       Cycle object to use for creating cycle on server.

        @return {object}            Returns a promise object which will resolve
                                    with either a success if the cycle was created
                                    on the server, or an error if the cycle could not be
                                    created on the server.

    */
    function create_cycle(cycle){
        var defer = $q.defer();
        $http({
            method: 'POST',
            url: '/app/cycles/',
            data: cycle,
            params: {
                organization_id: user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }


    /*  Update an existing a cycle in an organization

        @param {object} cycle   A cycle object with changed properties to update on server.
                                The object must include property 'id' for cycle ID.

        @return {object}        Returns a promise object which will resolve
                                with either a success if the cycle was updated,
                                or an error if not.
    */
    function update_cycle(cycle){
        var defer = $q.defer();
        $http({
            method: 'PUT',
            url: '/app/cycles/' + cycle.id + '/',
            data: cycle,
            params: {
                organization_id: user_service.get_organization().id
            }
        }).success(function(data, status, headers, config) {
            defer.resolve(data);
        }).error(function(data, status, headers, config) {
            defer.reject(data, status);
        });
        return defer.promise;
    }




    /* Public API */

    var cycle_factory = {

        //functions
        get_cycles : get_cycles,
        create_cycle : create_cycle,
        update_cycle : update_cycle

    };

    return cycle_factory;

}]);
