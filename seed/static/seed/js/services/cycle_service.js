/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.cycle', []).factory('cycle_service', [
  '$http',
  'user_service',
  function ($http, user_service) {

    var cycle_factory = {};
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

    cycle_factory.get_cycles = function () {
      return cycle_factory.get_cycles_for_org(user_service.get_organization().id);
    };

    cycle_factory.get_cycles_for_org = function (org_id) {
      return $http.get('/api/v3/cycles/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };


    /*  Add a cycle to an organization's list of cycles

     @param {object} cycle       Cycle object to use for creating cycle on server.

     @return {object}            Returns a promise object which will resolve
     with either a success if the cycle was created
     on the server, or an error if the cycle could not be
     created on the server.

     */
    cycle_factory.create_cycle = function (cycle) {
      return cycle_factory.create_cycle_for_org(cycle, user_service.get_organization().id);
    };

    cycle_factory.create_cycle_for_org = function (cycle, org_id) {
      return $http.post('/api/v3/cycles/', cycle, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };


    /*  Update an existing a cycle in an organization

     @param {object} cycle   A cycle object with changed properties to update on server.
     The object must include property 'id' for cycle ID.

     @return {object}        Returns a promise object which will resolve
     with either a success if the cycle was updated,
     or an error if not.
     */
    cycle_factory.update_cycle = function (cycle) {
      return cycle_factory.update_cycle_for_org(cycle, user_service.get_organization().id);
    };

    cycle_factory.update_cycle_for_org = function (cycle, org_id) {
      return $http.put('/api/v3/cycles/' + cycle.id + '/', cycle, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    cycle_factory.delete_cycle = function (cycle_id, org_id) {
      return $http.delete('/api/v3/cycles/' + cycle_id + '/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    return cycle_factory;

  }]);
