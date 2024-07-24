/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.service.map', []).factory('map_service', [
  '$http',
  ($http) => {
    // Save disadvantaged tract results to avoid unnecessary requests
    /** @type {Object.<string, boolean>} */
    const disadvantaged = {};

    /**
     * Fetch disadvantaged status of previously-unfetched tracts and cache locally
     * @param {[string]} tractIds
     * @returns {Promise<void>}
     */
    const checkDisadvantagedStatus = async (tractIds) => {
      const idsToFetch = tractIds.filter((id) => !(id in disadvantaged));
      // console.log(`Checking ${tractIds.length} tracts, fetching ${idsToFetch.length}`);
      if (idsToFetch.length) {
        const disadvantagedTracts = await $http
          .post('/api/v3/eeej/filter_disadvantaged_tracts/', {
            tract_ids: tractIds
          })
          .then(({ data: { disadvantaged: _disadvantaged } }) => _disadvantaged);
        for (const id of idsToFetch) {
          disadvantaged[id] = disadvantagedTracts.includes(id);
        }
      }
    };

    const isDisadvantaged = (tractId) => {
      if (tractId in disadvantaged) return disadvantaged[tractId];
      console.error(`Tract ${tractId} hasn't previously been fetched, run checkDisadvantagedStatus first`);
      return false;
    };

    return {
      checkDisadvantagedStatus,
      isDisadvantaged
    };
  }
]);
