/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/seed-platform/seed/main/LICENSE.md
 */
angular.module('BE.seed.service.ah', []).factory('ah_service', [
  () => {
    const { compare } = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

    const recurse_access_levels = (tree, access_level_instances_by_depth, depth = 1) => {
      if (!tree) return;
      if (!access_level_instances_by_depth[depth]) access_level_instances_by_depth[depth] = [];
      for (const ali of tree) {
        access_level_instances_by_depth[depth].push({ id: ali.id, name: ali.data.name });
        recurse_access_levels(ali.children, access_level_instances_by_depth, depth + 1);
      }
    };

    // Build out access_level_instances_by_depth recursively
    const calculate_access_level_instances_by_depth = (tree) => {
      const access_level_instances_by_depth = {};
      recurse_access_levels(tree, access_level_instances_by_depth);

      // Sort instances
      for (const [depth, instances] of Object.entries(access_level_instances_by_depth)) {
        access_level_instances_by_depth[depth] = instances.sort((a, b) => compare(a.name, b.name));
      }
      return access_level_instances_by_depth;
    };

    return {
      calculate_access_level_instances_by_depth
    };
  }
]);
