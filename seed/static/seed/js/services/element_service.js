/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.element', []).factory('element_service', [
  '$http',
  ($http) => ({
    // Return a list of elements for a given property
    get_elements: (organization_id, property_id) => $http
      .get(`/api/v3/properties/${property_id}/elements/`, {
        params: { organization_id }
      }).then(({ data }) => data),

    // Creates a new element for a given property
    create_element: (organization_id, property_id, element_data) => $http
      .post(`/api/v3/properties/${property_id}/elements/`, {
        ...element_data,
        organization_id
      }).then(({ data }) => data),

    // Updates an element for a given property
    update_element: (organization_id, property_id, element_id, element_data) => $http
      .put(`/api/v3/properties/${property_id}/elements/${element_id}/`, {
        ...element_data,
        organization_id
      }).then(({ data }) => data),

    // Deletes an element for a given property
    delete_element: (organization_id, property_id, element_id) => $http
      .delete(`/api/v3/properties/${property_id}/elements/${element_id}/`, {
        organization_id
      }).then(({ data }) => data)
  })
]);
