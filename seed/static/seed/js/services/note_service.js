/**
 * :copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.note', []).factory('note_service', [
  '$http',
  function ($http) {

    var note_factory = {};

    /*
      Return a list of notes for a giving property or taxlot

      {
        "created": "2018-01-11T21:00:16.178317Z",
        "id": 3,
        "log_data": {},
        "name": "name of note",
        "note_type": "Note",
        "organization_id": 1,
        "property_id": 1,
        "taxlot_id": null,
        "text": "this is a note",
        "updated": "2018-01-11T21:00:16.178345Z",
        "user_id": 1
      }
     */
    note_factory.get_notes = function (org_id, inventory_type, view_id) {
      return $http.get('/api/v2.1/' + inventory_type + '/' + view_id + /notes/, {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
        return response.data;
      });
    };

    note_factory.delete_note = function (inventory_type, view_id, note_id) {
      return $http.delete('/api/v2.1/' + inventory_type + '/' + view_id + /notes/ + note_id + '/', {}).then(function (response) {
        return response.data;
      });
    };

    /* create_note -- Creates a new note on the taxlot or property

      note data should have the following
      {
        "name": "Can be anything",
        "text": "Note data",
        "note_type": "Note"
      }

      There are other fields, but for now this is the basic required information
     */
    note_factory.create_note = function (org_id, inventory_type, view_id, note_data) {
      var payload = note_data;
      payload.organization_id = org_id;
      return $http.post('/api/v2.1/' + inventory_type + '/' + view_id + /notes/, payload).then(function (response) {
        return response.data;
      });
    };

    note_factory.update_note = function (org_id, inventory_type, view_id, note_id, note_data) {
      var payload = note_data;
      payload.organization_id = org_id;
      return $http.put('/api/v2.1/' + inventory_type + '/' + view_id + /notes/ + note_id + '/', payload).then(function (response) {
        return response.data;
      });
    };

    return note_factory;

  }]);
