BuildingSync
============

Several SEED processes use BuildingSync: Audit Template, BETTER, and BuildingSync file
import, name a few. When new releases of BuildingSync are made available,
SEED will need to be updated to use the new version. The following steps
will help you update SEED to use the new version of BuildingSync.

Note that the BuildingSync version update should be coordinated with Audit Template and BETTER.

Update Process
--------------

This process should be followed in the future when a new version of BuildingSync is released and needs to be added to SEED.

1. **Default BuildingSync version** - Update the BUILDINGSYNC_VERSION variable in config/settings/common.py.  This will be considered the “Default BuildingSync Version” throughout SEED (BETTER, BSync Import File, Audit Template).  This update must be coordinated with Audit Template or functionality could break.

2. Add the new buildingsync schema xsd file to: seed/building_sync/schema

3. Retrieve the enumerations.json from the BuildingSync schema release assets on GitHub (it's not in the repo, but it's in the 'assets' section of the  release in the Releases page). Add a version to the filename and store in seed/building_sync/enumerations.

4. Write a migration to add the new buildingsync measures from the new schema to the Measures table. This migration will reference the enumerations.json file you just added. As a guide, look at existing migration 0243.

5. Add a call to "populate_measures" function with the new schema version as argument, so that when new organizations are created, they will get populated with the measures for this new schema version. This is in seed/lib/superperms/orgs/models.py in class 'Organization' near line 337 (this could be better implemented in the future!)

6. Add a new constant for the new buildingsync version mapping in seed/building_sync/building_sync.py (around line 50 of the file). Also add an entry in the version_mapping_dict (line 59).

7. If a new mapping is necessary (for breaking changes, for example), add the new mapping to seed/building_sync/mappings.py.  Currently SEED only has “BASE_MAPPING_V2” which is used by all versions of BuildingSync that SEED supports. If there are breaking changes,  some of this functionality will need to be updated/redesigned to support multiple mappings.

8. **Building File (xml) processing** - seed/models/building_file.py.  This should be ok unless you skip versions of buildingsync, then it might break. The logic of the code where it determines which version of buildingsync to use for the measure look will need to be revised.  Currently, prior to v2.6.0 it will use version 1.0.0, but starting with 2.6.0 it will look for the specific version.

9. **Audit Template** (seed/audit_template/audit_template.py) - this pulls the buildingsync version from the settings file.  No changes should be needed here unless there are breaking changes or specific updates requested.

10. **BETTER** (seed/analysis_pipelines/better/buildingsync.py) - this pulls the buildingsync version from the settings file. Updating the version should just work, but test anyway and let BETTER team know so they can test/adjust the version on their end too. We want SEED-AT-BETTER all coordinated.

11. **BSYNCR Server** - Update bsyncr-server to latest version of BuildingSync by updating the building sync files in the bsyncr tests to v2.6.0 and running the test. Then update seed/analysis_pipelines/bsyncr.py to v2.6.0.

12. **BuildingSync Asset Extractor** - ok for now. It is currently on v2.4.0 of buildingsync but isn't checking versions. If breaking changes occur in the future, it will have to be updated to support multiple versions of BuildingSync to match what SEED does for BuildingSync File Import. https://github.com/BuildingSync/BuildingSync-asset-extractor

13. **BuildingSync Validator** - ok for now. This will automatically pull the default version from the settings file and update itself. The only consideration is that the BuildingSync.net validator is updated first to support the new version, but that shouldn't be an issue.

14. **Column Mapping Profiles** - ok for now, but would have to be updated/revised if there are ever breaking changes in the future.
