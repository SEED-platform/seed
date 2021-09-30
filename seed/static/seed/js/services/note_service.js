/**
 * :copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
 * :author
 */
angular.module('BE.seed.service.note', []).factory('note_service', [
  '$http',
  '$uibModal',
  'urls',
  function ($http, $uibModal, urls) {

    const note_factory = {};

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
      return $http.get('/api/v3/' + inventory_type + '/' + view_id + '/notes/', {
        params: {
          organization_id: org_id
        }
      }).then(function (response) {
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
      return $http.post('/api/v3/' + inventory_type + '/' + view_id + '/notes/', payload).then(function (response) {
        return response.data;
      });
    };

    note_factory.update_note = function (org_id, inventory_type, view_id, note_id, note_data) {
      var payload = note_data;
      payload.organization_id = org_id;
      return $http.put('/api/v3/' + inventory_type + '/' + view_id + '/notes/' + note_id + '/', payload).then(function (response) {
        return response.data;
      });
    };

    note_factory.delete_note = function (inventory_type, view_id, note_id) {
      return $http.delete('/api/v3/' + inventory_type + '/' + view_id + '/notes/' + note_id + '/', {}).then(function (response) {
        return response.data;
      });
    };

    note_factory.inventory_display_name = function (property_type, organization, item_state) {
      let error = '';
      let field = property_type === 'property' ? organization.property_display_field : organization.taxlot_display_field;
      if (!(field in item_state)) {
        error = field + ' does not exist';
        field = 'address_line_1';
      }
      if (!item_state[field]) {
        error += (error === '' ? '' : ' and default ') + field + ' is blank';
      }
      return item_state[field] ? item_state[field] : '(' + error + ') <i class="glyphicon glyphicon-question-sign" title="This can be changed from the organization settings page."></i>';
    };

    note_factory.open_create_note_modal = function (inventory_type, org_id, view_id) {
      return $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/inventory_detail_notes_modal.html',
        controller: 'inventory_detail_notes_modal_controller',
        size: 'lg',
        resolve: {
          inventoryType: _.constant(inventory_type),
          viewId: _.constant(view_id),
          orgId: _.constant(org_id),
          note: _.constant({text: ''}),
          action: _.constant('new')
        }
      }).result.then(function () {
        return note_factory.get_notes(org_id, inventory_type, view_id);
      });
    };

    note_factory.open_edit_note_modal = function (inventory_type, org_id, view_id, note) {
      return $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/inventory_detail_notes_modal.html',
        controller: 'inventory_detail_notes_modal_controller',
        size: 'lg',
        resolve: {
          inventoryType: _.constant(inventory_type),
          viewId: _.constant(view_id),
          orgId: _.constant(org_id),
          note: _.constant(note),
          action: _.constant('update')
        }
      }).result.then(function () {
        return note_factory.get_notes(org_id, inventory_type, view_id);
      });
    };

    note_factory.open_delete_note_modal = function (inventory_type, org_id, view_id, note) {
      return $uibModal.open({
        templateUrl: urls.static_url + 'seed/partials/inventory_detail_notes_modal.html',
        controller: 'inventory_detail_notes_modal_controller',
        size: 'lg',
        resolve: {
          inventoryType: _.constant(inventory_type),
          viewId: _.constant(view_id),
          orgId: _.constant(org_id),
          note: _.constant(note),
          action: _.constant('delete')
        }
      }).result.then(function () {
        return note_factory.get_notes(org_id, inventory_type, view_id);
      });
    };

    return note_factory;

  }]);
