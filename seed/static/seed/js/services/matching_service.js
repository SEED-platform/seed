/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.matching', []).factory('matching_service', [
  '$http',
  'user_service',
  'spinner_utility',
  // eslint-disable-next-line func-names
  function ($http, user_service, spinner_utility) {
    const matching_service = {};

    /**
     *Start system matching. For now, geocoding is also kicked off here.
     *
     *@param import_file_id: int, the database id of the import file
     * we wish to match against other buildings for an organization.
     */
    matching_service.start_system_matching = (import_file_id) => $http
      .post(
        `/api/v3/import_files/${import_file_id}/start_system_matching_and_geocoding/`,
        {},
        {
          params: { organization_id: user_service.get_organization().id }
        }
      )
      .then((response) => response.data)
      .catch((e) => e.data);

    matching_service.mergeProperties = (property_view_ids) => {
      spinner_utility.show();
      return $http
        .post(
          '/api/v3/properties/merge/',
          {
            property_view_ids
          },
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    matching_service.unmergeProperties = (view_id) => {
      spinner_utility.show();
      return $http
        .put(
          `/api/v3/properties/${view_id}/unmerge/`,
          {},
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    matching_service.mergeTaxlots = (taxlot_view_ids) => {
      spinner_utility.show();
      return $http
        .post(
          '/api/v3/taxlots/merge/',
          {
            taxlot_view_ids
          },
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    matching_service.unmergeTaxlots = (view_id) => {
      spinner_utility.show();
      return $http
        .post(
          `/api/v3/taxlots/${view_id}/unmerge/`,
          {},
          {
            params: {
              organization_id: user_service.get_organization().id
            }
          }
        )
        .then((response) => response.data)
        .finally(() => {
          spinner_utility.hide();
        });
    };

    return matching_service;
  }
]);
