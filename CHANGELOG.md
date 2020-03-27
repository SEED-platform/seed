# SEED Version 2.7.1

Date Range: 12/21/19 - 03/27/20

- Fixed [#94]( https://github.com/SEED-platform/seed/issues/94 ), Document how mapping works in the SEED-Platform / seed wiki
- Fixed [#994]( https://github.com/SEED-platform/seed/issues/994 ), It is possible to have orphaned user accounts without an associated organization
- Fixed [#1232]( https://github.com/SEED-platform/seed/issues/1232 ), Need easy way to view data year over year
- Feature [#1348]( https://github.com/SEED-platform/seed/issues/1348 ), DQ Checking -- for Valid data, not errors in data
- Fixed [#1480]( https://github.com/SEED-platform/seed/issues/1480 ), Five digit zip codes with leading 0
- Feature [#1591]( https://github.com/SEED-platform/seed/issues/1591 ), Detail Screen: Highlight the changes in the columns
- Fixed [#1592]( https://github.com/SEED-platform/seed/issues/1592 ), Prevent adding an org with existing name
- Fixed [#1713]( https://github.com/SEED-platform/seed/issues/1713 ), Return progress status immediately when uploading large files
- Feature [#1759]( https://github.com/SEED-platform/seed/issues/1759 ), Save mappings for specific input file data sources (ESPM, Tax Lot, Building List)
- Feature [#1760]( https://github.com/SEED-platform/seed/issues/1760 ), Save Reports to CSV / PNG files
- Feature [#1819]( https://github.com/SEED-platform/seed/issues/1819 ), DQ: Add label field to DQ Results Modal and Export file
- Fixed [#1899]( https://github.com/SEED-platform/seed/issues/1899 ), Import fields from BuildingSync reports
- Improved [#1913]( https://github.com/SEED-platform/seed/issues/1913 ), Add Notes info to export
- Fixed [#1932]( https://github.com/SEED-platform/seed/issues/1932 ), BRICR upload/download
- Fixed [#1933]( https://github.com/SEED-platform/seed/issues/1933 ), BRICR BuildingSync exports after Update with BuildingSync
- Fixed [#1946]( https://github.com/SEED-platform/seed/issues/1946 ), Meter data visible on some cycles but not all
- Maintenance [#1965]( https://github.com/SEED-platform/seed/issues/1965 ), Re-enable sentry on systems
- Fixed [#1975]( https://github.com/SEED-platform/seed/issues/1975 ), Tax Lot-specific merge check is inadvertently performed on properties
- Fixed [#1984]( https://github.com/SEED-platform/seed/issues/1984 ), 403 error when trying to view the Users in an Organization
- Fixed [#1992]( https://github.com/SEED-platform/seed/issues/1992 ), Data Mapping for imported files does not reflect the actual mapping for that data file
- Fixed [#1994]( https://github.com/SEED-platform/seed/issues/1994 ), Store timeseries data from scenarios
- Fixed [#1998]( https://github.com/SEED-platform/seed/issues/1998 ), First edit including lat long change doesn't trigger manual geocoding logic
- Fixed [#2009]( https://github.com/SEED-platform/seed/issues/2009 ), Update to Django 2.0.13
- Feature [#2013]( https://github.com/SEED-platform/seed/issues/2013 ), Notes: add option to delete notes
- Fixed [#2017]( https://github.com/SEED-platform/seed/issues/2017 ), Column Settings: Add ability to sort by Display Name or Column Name
- Fixed [#2018]( https://github.com/SEED-platform/seed/issues/2018 ), Geocoding Confidence in Master record are blank for merged records
- Fixed [#2023]( https://github.com/SEED-platform/seed/issues/2023 ), Data Import: when importing a new file to a dataset, default to the last cycle imported rather than the first cycle in the pulldown list
- Improved [#2027]( https://github.com/SEED-platform/seed/issues/2027 ), Column Settings: Improve Help Text at the top of the page
- Fixed [#2057]( https://github.com/SEED-platform/seed/issues/2057 ), Tax Lot Excel export 500 error
- Fixed [#2058]( https://github.com/SEED-platform/seed/issues/2058 ), Portfolio Manager URL Changed (Flapping Issue)
- Fixed [#2059]( https://github.com/SEED-platform/seed/issues/2059 ), Geocoding order changes aren't included in column setting change preview
- Fixed [#2060]( https://github.com/SEED-platform/seed/issues/2060 ), Column mapping preset creation during import not created with current snapshot
- Fixed [#2066]( https://github.com/SEED-platform/seed/issues/2066 ), Page not refreshed when switch menu tabs without saving changes and click on "stay on page"
- Fixed [#2069]( https://github.com/SEED-platform/seed/issues/2069 ), Selected Cycle not set on different inventory pages
- Fixed [#2072]( https://github.com/SEED-platform/seed/issues/2072 ), Inventory Detail no highlights for changes between extra_data
- Fixed [#2076]( https://github.com/SEED-platform/seed/issues/2076 ), ESPM import no longer works due to ESPM website updates
- Fixed [#2080]( https://github.com/SEED-platform/seed/issues/2080 ), Historical mapping page bug from mapping preset changes
- Fixed [#2082]( https://github.com/SEED-platform/seed/issues/2082 ), Static SEED Webpage Development
- Improved [#2084]( https://github.com/SEED-platform/seed/issues/2084 ), Print logs when CI fails
- Improved [#2089]( https://github.com/SEED-platform/seed/issues/2089 ), Add Best Practices to Documentation
- Fixed [#2091]( https://github.com/SEED-platform/seed/issues/2091 ), 500 Error Importing Tax Lot Data
- Fixed [#2095]( https://github.com/SEED-platform/seed/issues/2095 ), Upgrade Django and API-related dependencies
- Fixed [#2096]( https://github.com/SEED-platform/seed/issues/2096 ), Meter import bug - postgres unique constraints removed from meterreading table
- Feature [#2102]( https://github.com/SEED-platform/seed/issues/2102 ), Add "Freeze Master Column" feature in Detail View
- Fixed [#2105]( https://github.com/SEED-platform/seed/issues/2105 ), Error message when editing in Detail view is incomprehensible
- Fixed [#2114]( https://github.com/SEED-platform/seed/issues/2114 ), Deleting a rule after saving previous changes does not reactive save buttons
- Fixed [#2127]( https://github.com/SEED-platform/seed/issues/2127 ), Add functionality to see entire SEED HEADER field name in Mapping
- Fixed [#2131]( https://github.com/SEED-platform/seed/issues/2131 ), Bricr-dev testing for potential merge into develop
- Fixed [#2134]( https://github.com/SEED-platform/seed/issues/2134 ), Add new column setting to allow blank/'Not Available' values to overwrite other values
- Fixed [#2139]( https://github.com/SEED-platform/seed/issues/2139 ), Missing reverse match for password reset



# SEED Version 2.7.0-Beta

SEED Version 2.7.0-Beta includes several significant updates that need to be thoroughly tested on production data
before being deployed. The most notable changes:

- User can define which fields to match/merge/pair/link
- Properties and Tax Lots are not linked across multiple years or compliance cycles
- Users can define mapping profiles to save/recall mappings easier
- 55 closed issues/new features

Date Range: 09/30/19 - 12/20/19

Closed Issues and Features:
- Fixed [#94]( https://github.com/SEED-platform/seed/issues/94 ), Document how mapping works in the SEED-Platform / seed wiki
- Feature [#417]( https://github.com/SEED-platform/seed/issues/417 ), Reports -- Save the last settings
- Improved [#656]( https://github.com/SEED-platform/seed/issues/656 ), Add filename to modal reporting matches when there are no matches
- Feature [#709]( https://github.com/SEED-platform/seed/issues/709 ), Allow user to disable columns in import files and handle redundant column names in import files
- Fixed [#1024]( https://github.com/SEED-platform/seed/issues/1024 ), Can define user account without an organization
- Fixed [#1117]( https://github.com/SEED-platform/seed/issues/1117 ), Filter doesn't display all the rolled up data under some circumstances
- Improved [#1361]( https://github.com/SEED-platform/seed/issues/1361 ), Add a bit of space on left of mapping grid
- Fixed [#1375]( https://github.com/SEED-platform/seed/issues/1375 ), DQ Check - Save makes labels disappear on Admin Screen
- Improved [#1409]( https://github.com/SEED-platform/seed/issues/1409 ), Indicate that building/property records have merged/matched records
- Fixed [#1480]( https://github.com/SEED-platform/seed/issues/1480 ), Five digit zip codes with leading 0
- Fixed [#1511]( https://github.com/SEED-platform/seed/issues/1511 ), DQ results: Program doesn't tell user that a rule can't be applied due to data definition
- Improved [#1563]( https://github.com/SEED-platform/seed/issues/1563 ), Need an indicator that a filter has been applied to the data
- Fixed [#1571]( https://github.com/SEED-platform/seed/issues/1571 ), Update verbiage in dialog box(s) to reflect merging and pairing rather than matching
- Feature [#1715]( https://github.com/SEED-platform/seed/issues/1715 ), Add "Only Show Populated Columns" option to Detail List Settings
- Fixed [#1740]( https://github.com/SEED-platform/seed/issues/1740 ), Add UBID to BuildingSync and ensure it imports into SEED
- Fixed [#1817]( https://github.com/SEED-platform/seed/issues/1817 ), DQ: Program "hangs" when DQ rules can't be applied
- Fixed [#1818]( https://github.com/SEED-platform/seed/issues/1818 ), DQ: Program shows labels across all cycles in Filter by Labels list after running DQ check
- Fixed [#1845]( https://github.com/SEED-platform/seed/issues/1845 ), DQ Checking hanging in mapping due (possibly) to units issue
- Fixed [#1873]( https://github.com/SEED-platform/seed/issues/1873 ), data quality type error
- Fixed [#1945]( https://github.com/SEED-platform/seed/issues/1945 ), 403 (Forbidden) when trying to geocode records from Inventory List view
- Fixed [#1963]( https://github.com/SEED-platform/seed/issues/1963 ), Allow user to specify which fields are to be used for geocoding
- Maintenance [#1965]( https://github.com/SEED-platform/seed/issues/1965 ), Re-enable sentry on systems
- Fixed [#1970]( https://github.com/SEED-platform/seed/issues/1970 ), Problem importing a file into a specific org
- Fixed [#1977]( https://github.com/SEED-platform/seed/issues/1977 ), Review and update post-import file summary
- Fixed [#1979]( https://github.com/SEED-platform/seed/issues/1979 ), Detail View Edit of Custom ID 1 sometimes produces an error
- Fixed [#1982]( https://github.com/SEED-platform/seed/issues/1982 ), Display geojson map
- Fixed [#1989]( https://github.com/SEED-platform/seed/issues/1989 ), Unmerging records loses pairing
- Fixed [#1990]( https://github.com/SEED-platform/seed/issues/1990 ), Nonexistent properties/taxlots return bad responses
- Fixed [#1991]( https://github.com/SEED-platform/seed/issues/1991 ), Column Settings - Sort by MATCH CRITERIA needs some tweaks
- Fixed [#1996]( https://github.com/SEED-platform/seed/issues/1996 ), Release specific installation constraint of PostGIS docker container
- Fixed [#2005]( https://github.com/SEED-platform/seed/issues/2005 ), Unable to build docker image - Could not find library geos_c
- Fixed [#2010]( https://github.com/SEED-platform/seed/issues/2010 ), Mapping: Instructions: Group Matching fields by table
- Fixed [#2015]( https://github.com/SEED-platform/seed/issues/2015 ), Importing certain column names can break all future imports
- Fixed [#2031]( https://github.com/SEED-platform/seed/issues/2031 ), Importing mixed types with duplicate records can cause a 500
- Fixed [#2039]( https://github.com/SEED-platform/seed/issues/2039 ), Portfolio Manager Login URL Changed
- Fixed [#2052]( https://github.com/SEED-platform/seed/issues/2052 ), Column Settings: Saving Geocoding field definitions: getting 400 and 502 errrors
- Fixed [#1348]( https://github.com/SEED-platform/seed/issues/1348 ), DQ Checking -- for Valid data, not errors in data
- Fixed [#786]( https://github.com/SEED-platform/seed/issues/786 ), Save Changes button sequence in Data Cleansing Admin
- Fixed [#1998]( https://github.com/SEED-platform/seed/issues/1998 ), First edit including lat long change doesn't trigger manual geocoding logic
- Improved [#1592]( https://github.com/SEED-platform/seed/issues/1592 ), Prevent adding an org with existing name
- Fixed [#1592]( https://github.com/SEED-platform/seed/issues/1992 ), Data Mapping for imported files does not reflect the actual mapping for that data file
- Feature [#1591]( https://github.com/SEED-platform/seed/issues/1591 ), Detail Screen: Highlight the changes in the columns
- Feature [#1232]( https://github.com/SEED-platform/seed/issues/1232 ), Need easy way to view data year over year
- Fixed [#1946]( https://github.com/SEED-platform/seed/issues/1946 ), Meter data visible on some cycles but not all
- Feature [#1759]( https://github.com/SEED-platform/seed/issues/1759 ), Save mappings for specific input file data sources (ESPM, Tax Lot, Building List)
- Fixed [#994]( https://github.com/SEED-platform/seed/issues/994 ), It is possible to have orphaned user accounts without an associated organization
- Fixed [#2057]( https://github.com/SEED-platform/seed/issues/2057 ), Tax Lot Excel export 500 error
- Fixed [#1913]( https://github.com/SEED-platform/seed/issues/1913 ), Add Notes info to export
- Fixed [#1713]( https://github.com/SEED-platform/seed/issues/1713 ), Return progress status immediately when uploading large files

# SEED Version 2.6.1-Patch1

- Fixed [#2076]( https://github.com/SEED-platform/seed/issues/2076 ), ESPM import no longer works due to ESPM website updates

# SEED Version 2.6.1-Patch0

- This includes the patches from 2.6.0-patch0 since the patches were not complete until after the release of 2.6.1.
- Fixed [#2039]( https://github.com/SEED-platform/seed/issues/2039 ), Portfolio Manager Login URL Changed
- Fixed [#2058]( https://github.com/SEED-platform/seed/issues/2058 ), Portfolio Manager URL Changed (Flapping Issue)

# SEED Version 2.6.1

Date Range: 08/09/19 - 09/30/19

Closed Issues and Features:
- Fixed [#961]( https://github.com/SEED-platform/seed/issues/961 ), Inventory Detail UI Refinements
- Fixed [#1571]( https://github.com/SEED-platform/seed/issues/1571 ), Update verbiage in dialog box(s) to reflect merging and pairing rather than matching
- Fixed [#1844]( https://github.com/SEED-platform/seed/issues/1844 ), Can't map a field called Gross Floor Area without units
- Fixed [#1857]( https://github.com/SEED-platform/seed/issues/1857 ), Geocoding -- Tax Lot vs Property tables
- Fixed [#1883]( https://github.com/SEED-platform/seed/issues/1883 ), Can't create new users (as superuser)
- Fixed [#1942]( https://github.com/SEED-platform/seed/issues/1942 ), On import, duplicates are not flagged when ULID/UBIDs are involved
- Fixed [#1944]( https://github.com/SEED-platform/seed/issues/1944 ), ULID doesn't report that it could generate Lat/Long, but then does generate them
- Fixed [#1950]( https://github.com/SEED-platform/seed/issues/1950 ), ULID-only mapping - Geocoding confidence text is wrong

# SEED Version 2.6.0-patch0

This patch has address a couple issues including:

- Use previous version of base image for docker builds (both SEED and PostgreSQL). This is due to Ubuntu edge repo no long including the correct version of Postgis.
- Update the deployment to automatically read the version of redis, postgres, and OEP from the docker-compose.build.yml file
- Fix data comparisons when merging records
- Use OEP Version 1.4
- Fixed [#2039]( https://github.com/SEED-platform/seed/issues/2039 ), Portfolio Manager Login URL Changed
- Fixed [#2058]( https://github.com/SEED-platform/seed/issues/2058 ), Portfolio Manager URL Changed (Flapping Issue)
- Fixed [#2076]( https://github.com/SEED-platform/seed/issues/2076 ), ESPM import no longer works due to ESPM website updates

# SEED Version 2.6.0

Add time series related functionality. Make sure to review the [migrations.mst](docs/source/migrations.rst) on the upgrade.

Date Range: 05/04/19 - 08/09/19

Closed Issues and Features:
- Feature [#835]( https://github.com/SEED-platform/seed/issues/835 ), Expand default Portfolio Manager field mapping to include report for timeseries data
- Feature [#1861]( https://github.com/SEED-platform/seed/issues/1861 ), Allow renaming of columns
- Feature [#1871]( https://github.com/SEED-platform/seed/issues/1871 ), Allow redis passwords
- Feature [#1879]( https://github.com/SEED-platform/seed/issues/1879 ), profile_id as query param and part of v2.1 API
- Feature [#1888]( https://github.com/SEED-platform/seed/issues/1888 ), Export Measures and Scenario Data in XLSX Format
- Feature [#1917]( https://github.com/SEED-platform/seed/issues/1917 ), Importing ESPM Meter data for multiple buildings
- Feature [#1919]( https://github.com/SEED-platform/seed/issues/1919 ), Meter Feature Improvements
- Feature [#1927]( https://github.com/SEED-platform/seed/issues/1927 ), Make table headers sticky
- Feature [#1929]( https://github.com/SEED-platform/seed/issues/1929 ), Update BuildingSync to BuildingSync 2.0-pr1
- Improved [#1930]( https://github.com/SEED-platform/seed/issues/1930 ), Upgrade UBID Dependency to Latest
- Fixed [#442]( https://github.com/SEED-platform/seed/issues/442 ), Write unit test for simple_modal_service
- Fixed [#1844]( https://github.com/SEED-platform/seed/issues/1844 ), Can't map a field called Gross Floor Area without units
- Fixed [#1867]( https://github.com/SEED-platform/seed/issues/1867 ), Allow Bldg to be parsed as part of the normalized address
- Fixed [#1875]( https://github.com/SEED-platform/seed/issues/1875 ), Extra data not showing up in the pairing page
- Fixed [#1881]( https://github.com/SEED-platform/seed/issues/1881 ), Problem importing data
- Fixed [#1887]( https://github.com/SEED-platform/seed/issues/1887 ), Labels can be associated to Properties/TaxLots across Orgs (via Rules)
- Fixed [#1893]( https://github.com/SEED-platform/seed/issues/1893 ), Labels need to be associated to PropertyViews and TaxLotViews
- Fixed [#1894]( https://github.com/SEED-platform/seed/issues/1894 ), Meters could be lost during Property Merge and Unmerge
- Fixed [#1895]( https://github.com/SEED-platform/seed/issues/1895 ), Cannot import ESPM spreadsheets that have meter data
- Fixed [#1896]( https://github.com/SEED-platform/seed/issues/1896 ), Cannot import Green Button Data -- 500 error clicking on Energy link in Property Detail View
- Fixed [#1903]( https://github.com/SEED-platform/seed/issues/1903 ), 500 Internal Server Error trying to rename columns in Column Settings if the column already exists
- Fixed [#1912]( https://github.com/SEED-platform/seed/issues/1912 ), Error importing Green Button meter data
- Fixed [#1916]( https://github.com/SEED-platform/seed/issues/1916 ), Changed units for meters in Settings doesn't appear in the Inventory Meter view
- Fixed [#1918]( https://github.com/SEED-platform/seed/issues/1918 ), ESPM Meter Types that SEED doesn't recognize
- Fixed [#1920]( https://github.com/SEED-platform/seed/issues/1920 ), Incorrect meter display settings being used on Meter Detail Page.
- Fixed [#1922]( https://github.com/SEED-platform/seed/issues/1922 ), nginx page on staging
- Fixed [#1923]( https://github.com/SEED-platform/seed/issues/1923 ), Limit log files in Docker

# SEED Version 2.5.2

Date Range: 04/15/19 - 05/04/19

Closed Issues and Features:
- Feature [#1855]( https://github.com/SEED-platform/seed/issues/1855 ), Add ULID as a matching field on taxlots
- Feature [#1856]( https://github.com/SEED-platform/seed/issues/1856 ), Import building and taxlot footprints from WKT format
- Feature [#1861]( https://github.com/SEED-platform/seed/issues/1861 ), Allow renaming of columns
- Fixed [#1867]( https://github.com/SEED-platform/seed/issues/1867 ), Allow Bldg to be parsed as part of the normalized address

# SEED Version 2.5.1

Date Range: 03/28/19 - 04/15/19

Closed Issues and Features:
- Fixed [#1734]( https://github.com/SEED-platform/seed/issues/1734 ), segfault when loading a lot of records to view in Inventory List
- Fixed [#1815]( https://github.com/SEED-platform/seed/issues/1815 ), Property labels are not in the export file
- Feature [#1832]( https://github.com/SEED-platform/seed/issues/1832 ), Update BuildingSync to Version 1.0
- Feature [#1833]( https://github.com/SEED-platform/seed/issues/1833 ), Add ULID, Building Footprint, and Tax Lot Footprint to Database
- Feature [#1855]( https://github.com/SEED-platform/seed/issues/1855 ), Add ULID as a matching field on taxlots
- Feature [#1856]( https://github.com/SEED-platform/seed/issues/1856 ), Import building and taxlot footprints from WKT format

# SEED Version 2.5.0

Date Range: 02/19/19 - 03/27/19

Add GIS related functionality. Make sure to review the [migrations.mst](docs/source/migrations.rst) file on how to deploy the update.

Closed Issues:
- Fixed [#421]( https://github.com/SEED-platform/seed/issues/421 ), Reports - Message saying why there is no data
- Fixed [#1730]( https://github.com/SEED-platform/seed/issues/1730 ), Error importing BuildingSync File
- Fixed [#1734]( https://github.com/SEED-platform/seed/issues/1734 ), segfault when loading a lot of records to view in Inventory List
- Feature [#1741]( https://github.com/SEED-platform/seed/issues/1741 ), BuildingSync batch import from UI
- Fixed [#1811]( https://github.com/SEED-platform/seed/issues/1811 ), Unmerge Last doesn't work for BuildingSync XML files
- Fixed [#1812]( https://github.com/SEED-platform/seed/issues/1812 ), Merge screen doesn't show extra data fields
- Fixed [#1815]( https://github.com/SEED-platform/seed/issues/1815 ), Property labels are not in the export file
- Fixed [#1831]( https://github.com/SEED-platform/seed/issues/1831 ), Clean up database tables
- Feature [#1832]( https://github.com/SEED-platform/seed/issues/1832 ), Update BuildingSync to Version 1.0
- Fixed [#1833]( https://github.com/SEED-platform/seed/issues/1833 ), Add ULID, Building Footprint, and Tax Lot Footprint to Database
- Fixed [#1837]( https://github.com/SEED-platform/seed/issues/1837 ), Dimensionality Error
- Fixed [#1838]( https://github.com/SEED-platform/seed/issues/1838 ), Column Mappings can fail to load in the UI


# SEED Version 2.4.2

Date Range: 01/05/19 - 02/19/19

Closed Issues:
- Fixed [#421]( https://github.com/SEED-platform/seed/issues/421 ), Reports - Message saying why there is no data
- Fixed [#1124]( https://github.com/SEED-platform/seed/issues/1124 ), Linux install instructions
- Fixed [#1626]( https://github.com/SEED-platform/seed/issues/1626 ), 403 Error deleting Inventory from Org in Admin
- Fixed [#1730]( https://github.com/SEED-platform/seed/issues/1730 ), Error importing BuildingSync File
- Fixed [#1738]( https://github.com/SEED-platform/seed/issues/1738 ), No email sent to set password when I created a new organization
- Feature [#1741]( https://github.com/SEED-platform/seed/issues/1741 ), BuildingSync batch import from UI
- Feature [#1782]( https://github.com/SEED-platform/seed/issues/1782 ), Add OEI to docker deployment
- Fixed [#1797]( https://github.com/SEED-platform/seed/issues/1797 ), Ability to remove user who only belongs to a single organization
- Fixed [#1800]( https://github.com/SEED-platform/seed/issues/1800 ), Add managed task for adding user to organization via cli
- Feature [#1801]( https://github.com/SEED-platform/seed/issues/1801 ), Add dropdown for actions on inventory detail page
- Fixed [#1807]( https://github.com/SEED-platform/seed/issues/1807 ), Only fields in property or tax lot DB are shown in mapping screen (not showing Extra Data fields)
- Fixed [#1812]( https://github.com/SEED-platform/seed/issues/1812 ), Merge screen doesn't show extra data fields
- Fixed [#1813]( https://github.com/SEED-platform/seed/issues/1813 ), When merging records, the merged records don't show up in the detail view, only the final Master Record

# SEED Version 2.4.1

Date Range: 10/06/18 - 01/04/19:

Closed Issues:
- Fixed [#17]( https://github.com/SEED-platform/seed/issues/17 ), Ability to change mapping after it has been saved
- Fixed [#43]( https://github.com/SEED-platform/seed/issues/43 ), Internationalization of units
- Fixed [#343]( https://github.com/SEED-platform/seed/issues/343 ), Edit Organization Mappings screen -- add it
- Fixed [#1561]( https://github.com/SEED-platform/seed/issues/1561 ), Program Drops 2nd tax lot pairing (in mapping?) to do discarding duplicate tax lot record
- Fixed [#1594]( https://github.com/SEED-platform/seed/issues/1594 ), List view -- fields with long strings need popup like in building detail
- Fixed [#1645]( https://github.com/SEED-platform/seed/issues/1645 ), Release Date not being mapped as "Release Date" (defaulting to PM Release Date)
- Fixed [#1718]( https://github.com/SEED-platform/seed/issues/1718 ), Deleting all records for an org doesn't delete values in column settings
- Fixed [#1724]( https://github.com/SEED-platform/seed/issues/1724 ), KeyError: u'measures'
- Fixed [#1733]( https://github.com/SEED-platform/seed/issues/1733 ), Newly created column will not show up in API until data exists
- Fixed [#1739]( https://github.com/SEED-platform/seed/issues/1739 ), Admin Screen needs scroll bar at the bottom of the screen to scroll right
- Improved [#1743]( https://github.com/SEED-platform/seed/issues/1743 ), Remove deprecated repositories
- Fixed [#1767]( https://github.com/SEED-platform/seed/issues/1767 ), IDs for labels API return false
- Improved [#1768]( https://github.com/SEED-platform/seed/issues/1768 ), Upgrade to Python 3
- Improved [#1769]( https://github.com/SEED-platform/seed/issues/1769 ), Deploy script for docker stack deploy
- Fixed [#1770]( https://github.com/SEED-platform/seed/issues/1770 ), Update the update datetime field when changing tax lot or property
- Improved [#1771]( https://github.com/SEED-platform/seed/issues/1771 ), Remove Unused Django Models and Migration Code
- Fixed [#1772]( https://github.com/SEED-platform/seed/issues/1772 ), Return PropertyView ID from Label Filter API
- Fixed [#1773]( https://github.com/SEED-platform/seed/issues/1773 ), No measures in scenario break BuildingSync
- Improved [#1774]( https://github.com/SEED-platform/seed/issues/1774 ), Use alpine linux in Docker

# SEED Version 2.4.0

Date Range: 07/04/18 - 10/05/18:

Closed Issues: 32
- Fixed [#239]( https://github.com/SEED-platform/seed/issues/239 ), Rearchitect the progress API interactions
- Fixed [#711]( https://github.com/SEED-platform/seed/issues/711 ), Associating and disassociating orgs causes account to become disfuctional
- Fixed [#873]( https://github.com/SEED-platform/seed/issues/873 ), "NoneType object is not iterable" in _match_buildings
- Fixed [#876]( https://github.com/SEED-platform/seed/issues/876 ), Upgrade fine-uploader
- Fixed [#1172]( https://github.com/SEED-platform/seed/issues/1172 ), Mapping Review Screen - field name case and punctuation
- Fixed [#1200]( https://github.com/SEED-platform/seed/issues/1200 ), allow for user to manage column mappings
- Fixed [#1408]( https://github.com/SEED-platform/seed/issues/1408 ), DQ checking not working for specific case
- Fixed [#1497]( https://github.com/SEED-platform/seed/issues/1497 ), File hangs on matching
- Fixed [#1548]( https://github.com/SEED-platform/seed/issues/1548 ), ESPM Auto Import -- Import file name
- Fixed [#1565]( https://github.com/SEED-platform/seed/issues/1565 ), Error importing large ESPM file
- Fixed [#1582]( https://github.com/SEED-platform/seed/issues/1582 ), Reports not displaying data
- Fixed [#1585]( https://github.com/SEED-platform/seed/issues/1585 ), Error 400 when unmerging record
- Fixed [#1601]( https://github.com/SEED-platform/seed/issues/1601 ), Performance is quite slow moving between different views (Detail to List, etc)
- Fixed [#1608]( https://github.com/SEED-platform/seed/issues/1608 ), Improve Matching Performance
- Fixed [#1646]( https://github.com/SEED-platform/seed/issues/1646 ), Value edited in Detail view is overwritten when old data is again imported into SEED
- Fixed [#1654]( https://github.com/SEED-platform/seed/issues/1654 ), 500 Error when logging into ESPM from SEED
- Fixed [#1660]( https://github.com/SEED-platform/seed/issues/1660 ), Fields are not being displayed in the Detail view for either Property or Tax Lot
- Fixed [#1667]( https://github.com/SEED-platform/seed/issues/1667 ), DQ Export not working from Inventory List -- server failed error
- Fixed [#1668]( https://github.com/SEED-platform/seed/issues/1668 ), New Mapping Page layout makes it hard to compare the file header with the SEED header
- Fixed [#1672]( https://github.com/SEED-platform/seed/issues/1672 ), Inventory export -- Excel puts up error message, but then opens it
- Fixed [#1681]( https://github.com/SEED-platform/seed/issues/1681 ), Suborganization error message unclear
- Fixed [#1682]( https://github.com/SEED-platform/seed/issues/1682 ), Suborganization error uploading data
- Fixed [#1683]( https://github.com/SEED-platform/seed/issues/1683 ), SEED shouldn't allow suborgs of suborgs
- Fixed [#1685]( https://github.com/SEED-platform/seed/issues/1685 ), Import Building Sync file from Audit Report Template
- Fixed [#1686]( https://github.com/SEED-platform/seed/issues/1686 ), Suborganization list settings don't work
- Fixed [#1689]( https://github.com/SEED-platform/seed/issues/1689 ), Importing file with crlf and blank line returns causes errors
- Fixed [#1692]( https://github.com/SEED-platform/seed/issues/1692 ), Error clicking "i" Nav Button
- Fixed [#1694]( https://github.com/SEED-platform/seed/issues/1694 ), Settings profile field list is reversed on save when saving the first Settings Profile
- Fixed [#1696]( https://github.com/SEED-platform/seed/issues/1696 ), 502 error displaying inventory in org with large number of records
- Fixed [#1698]( https://github.com/SEED-platform/seed/issues/1698 ), Add the ability to not overwrite the data by column on merge
- Fixed [#1702]( https://github.com/SEED-platform/seed/issues/1702 ), Test the spinner visibility during routing transitions
- Fixed [#1707]( https://github.com/SEED-platform/seed/issues/1707 ), Site EUI (kBtu/ft²) & Source EUI (kBtu/ft²) fields are not imported with autoimport from ESPM

Accepted Pull Requests: 25
- Fixed [#1661]( https://github.com/SEED-platform/seed/pull/1661 ), Address PM Import Error
- Fixed [#1674]( https://github.com/SEED-platform/seed/pull/1674 ), Report proper filename for uploaded_filename during PM import
- Fixed [#1676]( https://github.com/SEED-platform/seed/pull/1676 ), Improve progress bar functionality
- Fixed [#1677]( https://github.com/SEED-platform/seed/pull/1677 ), ID in CSV causing Excel to throw warnings
- Fixed [#1680]( https://github.com/SEED-platform/seed/pull/1680 ), Remove unused classes and cleanup deprecated code
- Fixed [#1684]( https://github.com/SEED-platform/seed/pull/1684 ), Hash object upon save
- Fixed [#1687]( https://github.com/SEED-platform/seed/pull/1687 ), Fix and cleanup suborganizations
- Fixed [#1688]( https://github.com/SEED-platform/seed/pull/1688 ), Buildingsync upload merge develop
- Fixed [#1690]( https://github.com/SEED-platform/seed/pull/1690 ), Fix first_five_rows method to be more flexible
- Fixed [#1691]( https://github.com/SEED-platform/seed/pull/1691 ), Fix privilege escalation bug
- Fixed [#1695]( https://github.com/SEED-platform/seed/pull/1695 ), Add transactions
- Fixed [#1697]( https://github.com/SEED-platform/seed/pull/1697 ), BuildingSync Upload
- Fixed [#1699]( https://github.com/SEED-platform/seed/pull/1699 ), Field by field merging preferences
- Fixed [#1700]( https://github.com/SEED-platform/seed/pull/1700 ), Fixed the spinner visibility during routing transitions
- Fixed [#1701]( https://github.com/SEED-platform/seed/pull/1701 ), Inventory Performance
- Fixed [#1703]( https://github.com/SEED-platform/seed/pull/1703 ), Strip spaces around value before typecasting
- Fixed [#1704]( https://github.com/SEED-platform/seed/pull/1704 ), Change default org to user first org available
- Fixed [#1705]( https://github.com/SEED-platform/seed/pull/1705 ), Inventory View Fixes
- Fixed [#1706]( https://github.com/SEED-platform/seed/pull/1706 ), Create default columns managed task, fix unicode error in mapping
- Fixed [#1708]( https://github.com/SEED-platform/seed/pull/1708 ), Update BuildingSync Upload
- Fixed [#1709]( https://github.com/SEED-platform/seed/pull/1709 ), Fix the reversed column order when saving a new settings profile
- Fixed [#1710]( https://github.com/SEED-platform/seed/pull/1710 ), Fix csv import
- Fixed [#1714]( https://github.com/SEED-platform/seed/pull/1714 ), Docker timeouts
- Fixed [#1720]( https://github.com/SEED-platform/seed/pull/1720 ), Fix pint cleaner and mapping error
- Fixed [#1721]( https://github.com/SEED-platform/seed/pull/1721 ), Handle Duplicate Measure IDs in BuildingSync Uploads

# SEED Version 2.3.3

Date Range: 05/31/18 - 07/04/18:

Closed Issues: 18
- Fixed [#74]( https://github.com/SEED-platform/seed/issues/74 ), Update Projects when new data is added
- Fixed [#127]( https://github.com/SEED-platform/seed/issues/127 ), Export unmatched records
- Fixed [#258]( https://github.com/SEED-platform/seed/issues/258 ), Add Buildings to Projects from Project Screen
- Fixed [#285]( https://github.com/SEED-platform/seed/issues/285 ), Incorrect event for delete project?
- Fixed [#360]( https://github.com/SEED-platform/seed/issues/360 ), Duplicate Data -- Cleanup after importing files
- Fixed [#590]( https://github.com/SEED-platform/seed/issues/590 ), deleting data sets does not delete buildings?
- Fixed [#654]( https://github.com/SEED-platform/seed/issues/654 ), Design feature which allows bulk editing of data
- Fixed [#829]( https://github.com/SEED-platform/seed/issues/829 ), Building project tab shouldn't have edit button
- Fixed [#838]( https://github.com/SEED-platform/seed/issues/838 ), Edit project window doesn't pre-populate compliance fields
- Fixed [#1282]( https://github.com/SEED-platform/seed/issues/1282 ), Add space to the left of the Settings grids
- Fixed [#1292]( https://github.com/SEED-platform/seed/issues/1292 ), Blank record added to Tax Lot view
- Fixed [#1344]( https://github.com/SEED-platform/seed/issues/1344 ), Error trying to display inventory list
- Fixed [#1414]( https://github.com/SEED-platform/seed/issues/1414 ), get_api_request_user in seed/utils/api.py fails with UnboundLocalError when HTTP_AUTHORIZATION is not basic
- Fixed [#1587]( https://github.com/SEED-platform/seed/issues/1587 ), Mapping: If columns are mapped to both Property and Taxlot tables, ensure that a matching field is present for each table
- Fixed [#1656]( https://github.com/SEED-platform/seed/issues/1656 ), Update Version number to 2.3.2
- Fixed [#1663]( https://github.com/SEED-platform/seed/issues/1663 ), Program hangs at 100% on mapping
- Fixed [#1665]( https://github.com/SEED-platform/seed/issues/1665 ), DQ not working -- fields don't display in admin, 500 server error when running in inventory
- Fixed [#1669]( https://github.com/SEED-platform/seed/issues/1669 ), Export from Actions pulldown not working on dev1 branch

Accepted Pull Requests: 7
- Fixed [#1653]( https://github.com/SEED-platform/seed/pull/1653 ), Generates PM Import file name based on date
- Fixed [#1655]( https://github.com/SEED-platform/seed/pull/1655 ), Fixed the angular-sanitize semantic versioning
- Fixed [#1658]( https://github.com/SEED-platform/seed/pull/1658 ), Fix Migration for Production Data
- Fixed [#1659]( https://github.com/SEED-platform/seed/pull/1659 ), Major mapping improvements
- Fixed [#1662]( https://github.com/SEED-platform/seed/pull/1662 ), Return inventory records with only the columns specified
- Fixed [#1666]( https://github.com/SEED-platform/seed/pull/1666 ), Data Quality Checks Returned 500
- Fixed [#1670]( https://github.com/SEED-platform/seed/pull/1670 ), Fix Inventory Export and Displaying of Extra Data Fields in Inventory

# SEED Version 2.3.2

Closed Issues: 80
- Fixed [#28]( https://github.com/SEED-platform/seed/issues/28 ), Show source data file of unmatched records in Building Detail
- Fixed [#60]( https://github.com/SEED-platform/seed/issues/60 ), In record list shown in matching, only show fields present in the data file
- Fixed [#93]( https://github.com/SEED-platform/seed/issues/93 ), MAPPING: Add a "clear mapping" button
- Fixed [#209]( https://github.com/SEED-platform/seed/issues/209 ), Checkboxes are too small
- Fixed [#217]( https://github.com/SEED-platform/seed/issues/217 ), Add export to Matching screen
- Fixed [#269]( https://github.com/SEED-platform/seed/issues/269 ), Add date of import to building detail list
- Fixed [#270]( https://github.com/SEED-platform/seed/issues/270 ), Add Matching functionality to Building List
- Fixed [#308]( https://github.com/SEED-platform/seed/issues/308 ), UI for Log Files for Duplicate Data
- Fixed [#445]( https://github.com/SEED-platform/seed/issues/445 ), Normalize BE endpoint success responses
- Fixed [#506]( https://github.com/SEED-platform/seed/issues/506 ), Data cleansing criteria additions and issues
- Fixed [#527]( https://github.com/SEED-platform/seed/issues/527 ), Bugs related to recently implemented caching utilities
- Fixed [#538]( https://github.com/SEED-platform/seed/issues/538 ), Updating master record with multiple PM files - auto vs hand matching
- Fixed [#543]( https://github.com/SEED-platform/seed/issues/543 ), When should program overwrite existing data when matching records?
- Fixed [#579]( https://github.com/SEED-platform/seed/issues/579 ), Add ability to view different fields on each side of matching screen
- Fixed [#631]( https://github.com/SEED-platform/seed/issues/631 ), Investigate the options for automatically downloading Custom Reporting Template data from Portfolio Manager
- Fixed [#636]( https://github.com/SEED-platform/seed/issues/636 ), Improvements to Matching Screen
- Fixed [#639]( https://github.com/SEED-platform/seed/issues/639 ), Matching view still has 'active' filter inputs.
- Fixed [#647]( https://github.com/SEED-platform/seed/issues/647 ), Add ability to delete unmatched records from the matching screen
- Fixed [#677]( https://github.com/SEED-platform/seed/issues/677 ), Two Building records can't both match to one PM record
- Fixed [#707]( https://github.com/SEED-platform/seed/issues/707 ), Can't map files
- Fixed [#807]( https://github.com/SEED-platform/seed/issues/807 ), Review Mapped Data doesn't show all mapped fields
- Fixed [#839]( https://github.com/SEED-platform/seed/issues/839 ), Server error searching by date fields on seed production but not seedtest
- Fixed [#844]( https://github.com/SEED-platform/seed/issues/844 ), Thoughts about UI for Timeseries feature
- Fixed [#845]( https://github.com/SEED-platform/seed/issues/845 ), Field is added to Master Building record even if it is unchecked in mapping
- Fixed [#898]( https://github.com/SEED-platform/seed/issues/898 ), Don't automatically make unmatched records into new buildings
- Fixed [#927]( https://github.com/SEED-platform/seed/issues/927 ), Change Read the Docs subdomain
- Fixed [#937]( https://github.com/SEED-platform/seed/issues/937 ), DB Refactoring -- Audit Logs and Data Migration
- Fixed [#962]( https://github.com/SEED-platform/seed/issues/962 ), Date filtering not working in Mozilla Firefox
- Fixed [#1027]( https://github.com/SEED-platform/seed/issues/1027 ), Can't delete data in extra_data fields in Building Detail
- Fixed [#1035]( https://github.com/SEED-platform/seed/issues/1035 ), Stay in the same place in the building list when coming back from building detail
- Fixed [#1039]( https://github.com/SEED-platform/seed/issues/1039 ), Swagger is inelegant when user isn't logged in
- Fixed [#1048]( https://github.com/SEED-platform/seed/issues/1048 ), Figure out what SEED is using prefinery.com for
- Fixed [#1142]( https://github.com/SEED-platform/seed/issues/1142 ), Update rest framework swagger
- Fixed [#1160]( https://github.com/SEED-platform/seed/issues/1160 ), Mapping Review screen is empty possibly when all fields are extra data
- Fixed [#1191]( https://github.com/SEED-platform/seed/issues/1191 ), Return display names from the backend
- Fixed [#1198]( https://github.com/SEED-platform/seed/issues/1198 ), Authentication is broken when using an api key
- Fixed [#1229]( https://github.com/SEED-platform/seed/issues/1229 ), Issue with Mapping a second time
- Fixed [#1235]( https://github.com/SEED-platform/seed/issues/1235 ), Add option to save display settings across org, so it isn't just for your account / browser
- Fixed [#1260]( https://github.com/SEED-platform/seed/issues/1260 ), Default checked fields in List and Detail settings to fields that have been mapped?
- Fixed [#1265]( https://github.com/SEED-platform/seed/issues/1265 ), Program is automatically mapping Energy score to ENERGY STAR Score but it doesn't display in mapping
- Fixed [#1277]( https://github.com/SEED-platform/seed/issues/1277 ), Importing sample test files, many issues -- can break into smaller issues as needed
- Fixed [#1297]( https://github.com/SEED-platform/seed/issues/1297 ), Data quality errors when typecasting data (TypeError Str -> Float)
- Fixed [#1302]( https://github.com/SEED-platform/seed/issues/1302 ), Add number of records imported to Import "Successful" dialog box
- Fixed [#1314]( https://github.com/SEED-platform/seed/issues/1314 ), Hand matching / unmatching for migrated data
- Fixed [#1337]( https://github.com/SEED-platform/seed/issues/1337 ), SEED Header input box in Mapping -- need to be able to make column wide enough to see long field names
- Fixed [#1340]( https://github.com/SEED-platform/seed/issues/1340 ), Can't Create new organization as superuser with existing email
- Fixed [#1362]( https://github.com/SEED-platform/seed/issues/1362 ), DQ Check - Allow sorting by column in DQ results modal
- Fixed [#1403]( https://github.com/SEED-platform/seed/issues/1403 ), List Settings are tedious to rework
- Fixed [#1406]( https://github.com/SEED-platform/seed/issues/1406 ), List views - wrap text or show text in bubble
- Fixed [#1423]( https://github.com/SEED-platform/seed/issues/1423 ), Spinner needs to display longer when program is working to display Matching Detail screen
- Fixed [#1450]( https://github.com/SEED-platform/seed/issues/1450 ), Need spinner when changing cycles in Inventory list for large datasets
- Fixed [#1464]( https://github.com/SEED-platform/seed/issues/1464 ), Field mapping -- Letter after number gets capitalized
- Fixed [#1495]( https://github.com/SEED-platform/seed/issues/1495 ), Mapping / List Setting issues
- Fixed [#1532]( https://github.com/SEED-platform/seed/issues/1532 ), Auto ESPM import doesn't add data to correct Cycle
- Fixed [#1543]( https://github.com/SEED-platform/seed/issues/1543 ), Export not returning all data when exporting from taxlot view
- Fixed [#1547]( https://github.com/SEED-platform/seed/issues/1547 ), Matching Review -- 0 tax lots when there should be 9
- Fixed [#1549]( https://github.com/SEED-platform/seed/issues/1549 ), Add UBID to Mapping screen explanation for matching fields
- Fixed [#1560]( https://github.com/SEED-platform/seed/issues/1560 ), Can't "deselect" the filter buttons AND/OR/EXCLUDE
- Fixed [#1566]( https://github.com/SEED-platform/seed/issues/1566 ), Need to be able to save different List Setting configurations
- Fixed [#1567]( https://github.com/SEED-platform/seed/issues/1567 ), Show labels in List view
- Fixed [#1570]( https://github.com/SEED-platform/seed/issues/1570 ), Show records most recently imported from ESPM
- Fixed [#1573]( https://github.com/SEED-platform/seed/issues/1573 ), Upload your data modal tweaks
- Fixed [#1574]( https://github.com/SEED-platform/seed/issues/1574 ), Inventory List View -- Default List Settings should show mapped fields
- Fixed [#1577]( https://github.com/SEED-platform/seed/issues/1577 ), Admin Function -- 403 error removing user
- Fixed [#1578]( https://github.com/SEED-platform/seed/issues/1578 ), Admin Function -- Error adding existing user to existing organization
- Fixed [#1583]( https://github.com/SEED-platform/seed/issues/1583 ), Unable to log into ESPM account from SEED
- Fixed [#1586]( https://github.com/SEED-platform/seed/issues/1586 ), Cycle range for new orgs is incorrect
- Fixed [#1588]( https://github.com/SEED-platform/seed/issues/1588 ), Columns with the same name in different tables should correctly differentiate the data
- Fixed [#1596]( https://github.com/SEED-platform/seed/issues/1596 ), Add Lat/Long to PropertyState
- Fixed [#1603]( https://github.com/SEED-platform/seed/issues/1603 ), Unable to view swagger page when not logged in
- Fixed [#1606]( https://github.com/SEED-platform/seed/issues/1606 ), Save List Settings in List and Detail View
- Fixed [#1613]( https://github.com/SEED-platform/seed/issues/1613 ), Associated tax lot ID in Mapping Review is confusing to users
- Fixed [#1621]( https://github.com/SEED-platform/seed/issues/1621 ), PM Report Template list -- not all the reports are listed in SEED
- Fixed [#1627]( https://github.com/SEED-platform/seed/issues/1627 ), Tax Lot list Settings Profile Saving -- internal server error
- Fixed [#1632]( https://github.com/SEED-platform/seed/issues/1632 ), Units are off for Energy Use and EUI when using the ESPM Login from SEED to import data
- Fixed [#1633]( https://github.com/SEED-platform/seed/issues/1633 ), Pairing between 1 Tax Lot ID and Multiple UBIDs does not seem to be working
- Fixed [#1634]( https://github.com/SEED-platform/seed/issues/1634 ), Mapping hangs at 100% complete -- organization ID doesn't exist
- Fixed [#1635]( https://github.com/SEED-platform/seed/issues/1635 ), ValueError: Cannot assign "269": "DataQualityCheck.organization" must be a "Organization" instance.
- Fixed [#1639]( https://github.com/SEED-platform/seed/issues/1639 ), Unmerge only works once on a given property record
- Fixed [#1649]( https://github.com/SEED-platform/seed/issues/1649 ), Importing Data with the Same Address on Multiple Rows do not track lot_numbers

Accepted Pull Requests: 30
- Fixed [#1581]( https://github.com/SEED-platform/seed/pull/1581 ), Improved error messages for admin.html
- Fixed [#1597]( https://github.com/SEED-platform/seed/pull/1597 ), Allow the mapping columns to be resizable
- Fixed [#1598]( https://github.com/SEED-platform/seed/pull/1598 ), Add export issues script
- Fixed [#1599]( https://github.com/SEED-platform/seed/pull/1599 ), Show only populated columns
- Fixed [#1602]( https://github.com/SEED-platform/seed/pull/1602 ), Updated translation files
- Fixed [#1604]( https://github.com/SEED-platform/seed/pull/1604 ), Fix data quality typeerror
- Fixed [#1605]( https://github.com/SEED-platform/seed/pull/1605 ), Fix swagger access
- Fixed [#1610]( https://github.com/SEED-platform/seed/pull/1610 ), Add libffi-dev and libssl-dev to docker and documentation
- Fixed [#1611]( https://github.com/SEED-platform/seed/pull/1611 ), Remove unneeded auth classes. Fix BuildingSync and HPXML API endpoints
- Fixed [#1618]( https://github.com/SEED-platform/seed/pull/1618 ), Add Latitude and Longitude to Database Fields
- Fixed [#1622]( https://github.com/SEED-platform/seed/pull/1622 ), Add column display names to the database
- Fixed [#1623]( https://github.com/SEED-platform/seed/pull/1623 ), List Settings Profiles + Display Names Refactor
- Fixed [#1624]( https://github.com/SEED-platform/seed/pull/1624 ), New Oganization Cycle Range
- Fixed [#1625]( https://github.com/SEED-platform/seed/pull/1625 ), Fix portfolio manager child data request
- Fixed [#1628]( https://github.com/SEED-platform/seed/pull/1628 ), Fixed missing pinned parameter when the value is undefined
- Fixed [#1629]( https://github.com/SEED-platform/seed/pull/1629 ), Fix race condition on creating DataQualityCheck objects
- Fixed [#1630]( https://github.com/SEED-platform/seed/pull/1630 ), Superuser improvements
- Fixed [#1631]( https://github.com/SEED-platform/seed/pull/1631 ), Fix `Only Show Populated` to use the current cycle
- Fixed [#1636]( https://github.com/SEED-platform/seed/pull/1636 ), Fix organization in DataQualityCheck
- Fixed [#1637]( https://github.com/SEED-platform/seed/pull/1637 ), Use kBtu during imports for PM
- Fixed [#1638]( https://github.com/SEED-platform/seed/pull/1638 ), Fixed showing of default pairing columns
- Fixed [#1650]( https://github.com/SEED-platform/seed/pull/1650 ), Allow import of multiple ubids, single taxlot in CSV
- Fixed [#1651]( https://github.com/SEED-platform/seed/pull/1651 ), Ensure mapping to both TaxLot and PropertyState columns is enforced

Accepted External Pull Requests: 5
- Fixed [#1536]( https://github.com/SEED-platform/seed/pull/1536 ), Quantity (aka. Pint) fields to accommodate metric and US Customary energy/area data
- Fixed [#1609]( https://github.com/SEED-platform/seed/pull/1609 ), Added oauth, add_columns endpoint, and adjusted pint handling
- Fixed [#1616]( https://github.com/SEED-platform/seed/pull/1616 ), filterset update to find PropertyView by various PropertyState building
- Fixed [#1617]( https://github.com/SEED-platform/seed/pull/1617 ), Made PropertyStateWritableSerializer fields not required
- Fixed [#1620]( https://github.com/SEED-platform/seed/pull/1620 ), Fix add_columns endpoint

# SEED Version 2.3.1

Closed Issues: 4
- Fixed [#1289]( https://github.com/SEED-platform/seed/issues/1289 ), Filter on numeric fields
- Fixed [#1321]( https://github.com/SEED-platform/seed/issues/1321 ), Hand Matching screen -- Fix field headers, add vertical scroll bar, other UI improvements
- Fixed [#1524]( https://github.com/SEED-platform/seed/issues/1524 ), Editing record in inventory view corrupts the record
- Fixed [#1576]( https://github.com/SEED-platform/seed/issues/1576 ), Rework Exporting from Hamburger view

Accepted Pull Requests: 8
- Fixed [#1551]( https://github.com/SEED-platform/seed/pull/1551 ), Added UBID to the mapping instructions
- Fixed [#1552]( https://github.com/SEED-platform/seed/pull/1552 ), Fixed the count for the imported number of mapped tax lots
- Fixed [#1556]( https://github.com/SEED-platform/seed/pull/1556 ), Add date to PM import filename
- Fixed [#1557]( https://github.com/SEED-platform/seed/pull/1557 ), Release 2.3
- Fixed [#1558]( https://github.com/SEED-platform/seed/pull/1558 ), Notes Improvements
- Fixed [#1559]( https://github.com/SEED-platform/seed/pull/1559 ), Cleanup Travis
- Fixed [#1562]( https://github.com/SEED-platform/seed/pull/1562 ), Added UBID to the mapping instructions
- Fixed [#1564]( https://github.com/SEED-platform/seed/pull/1564 ), Temporarily hid the `Upload Green Button Data` button

# SEED Version 2.3

Closed Issues: 21
- Fixed [#148]( https://github.com/SEED-platform/seed/issues/148 ), For PM mapping, add feature to remember user defined mappings
- Fixed [#179]( https://github.com/SEED-platform/seed/issues/179 ), Auto-connect to Portfolio Manager
- Fixed [#1125]( https://github.com/SEED-platform/seed/issues/1125 ), Mapping suggestions are improved but could still be improved
- Fixed [#1231]( https://github.com/SEED-platform/seed/issues/1231 ), Inventory Detail: Add Log & Notes back
- Fixed [#1238]( https://github.com/SEED-platform/seed/issues/1238 ), Add option in mapping to map all fields to original file field names
- Fixed [#1298]( https://github.com/SEED-platform/seed/issues/1298 ), Add Import Date as a viewable field in List and Detail view
- Fixed [#1328]( https://github.com/SEED-platform/seed/issues/1328 ), Filter operators -- make them the same for numeric and strings
- Fixed [#1385]( https://github.com/SEED-platform/seed/issues/1385 ), Hand Matching -- need to be able to match multiple records together (V 1.5 feature)
- Fixed [#1396]( https://github.com/SEED-platform/seed/issues/1396 ), Add Unique Building ID as a matching field
- Fixed [#1499]( https://github.com/SEED-platform/seed/issues/1499 ), Functionality different between two servers with same deployment
- Fixed [#1501]( https://github.com/SEED-platform/seed/issues/1501 ), migrate django password reset to class based views
- Fixed [#1509]( https://github.com/SEED-platform/seed/issues/1509 ), Mapped fields with underscore are transformed to a field name without underscore
- Fixed [#1510]( https://github.com/SEED-platform/seed/issues/1510 ), Export all data as CSV file not working as expected
- Fixed [#1512]( https://github.com/SEED-platform/seed/issues/1512 ), Export has (primarily) internal field names not SEED user mapped field names
- Fixed [#1525]( https://github.com/SEED-platform/seed/issues/1525 ), merging code caused merging issue
- Fixed [#1527]( https://github.com/SEED-platform/seed/issues/1527 ), non-deterministic test
- Fixed [#1529]( https://github.com/SEED-platform/seed/issues/1529 ), requires_member when viewing organization
- Fixed [#1549]( https://github.com/SEED-platform/seed/issues/1549 ), Add UBID to Mapping screen explanation for matching fields
- Fixed [#1550]( https://github.com/SEED-platform/seed/issues/1550 ), UBID Upper/lower case field name in mapping
- Fixed [#1554]( https://github.com/SEED-platform/seed/issues/1554 ), Add UBID to Pairing screen
- Fixed [#1555]( https://github.com/SEED-platform/seed/issues/1555 ), Unmerging Tax Lots doesn't unpair the records paired when records were merged

Accepted Pull Requests: 25
- Fixed [#1491]( https://github.com/SEED-platform/seed/pull/1491 ), BRICR Support - BuildingSync, Measures, Scenarios, etc.
- Fixed [#1492]( https://github.com/SEED-platform/seed/pull/1492 ), OGBS - French (Canada) localization
- Fixed [#1507]( https://github.com/SEED-platform/seed/pull/1507 ), removing instruction to python setup.py install
- Fixed [#1513]( https://github.com/SEED-platform/seed/pull/1513 ), Integration with Portfolio Manager
- Fixed [#1515]( https://github.com/SEED-platform/seed/pull/1515 ), 1298 import date field
- Fixed [#1517]( https://github.com/SEED-platform/seed/pull/1517 ), Bricr buildingsync upload
- Fixed [#1519]( https://github.com/SEED-platform/seed/pull/1519 ), save pm mapping changes to database.
- Fixed [#1520]( https://github.com/SEED-platform/seed/pull/1520 ), Translation example
- Fixed [#1521]( https://github.com/SEED-platform/seed/pull/1521 ), Add UBID
- Fixed [#1526]( https://github.com/SEED-platform/seed/pull/1526 ), Update ubid in example files
- Fixed [#1528]( https://github.com/SEED-platform/seed/pull/1528 ), view history
- Fixed [#1530]( https://github.com/SEED-platform/seed/pull/1530 ), Shared Field Settings Page
- Fixed [#1531]( https://github.com/SEED-platform/seed/pull/1531 ), Add Queued State to Analysis State
- Fixed [#1533]( https://github.com/SEED-platform/seed/pull/1533 ), Fixed the selected cycle for PM imports
- Fixed [#1534]( https://github.com/SEED-platform/seed/pull/1534 ), Combined text/numeric filtering
- Fixed [#1535]( https://github.com/SEED-platform/seed/pull/1535 ), display analysis state string instead of int
- Fixed [#1537]( https://github.com/SEED-platform/seed/pull/1537 ), Re-sorts angular localization files
- Fixed [#1538]( https://github.com/SEED-platform/seed/pull/1538 ), Updated copyrights
- Fixed [#1539]( https://github.com/SEED-platform/seed/pull/1539 ), Add Notes Field
- Fixed [#1540]( https://github.com/SEED-platform/seed/pull/1540 ), Hand-merge multiple records
- Fixed [#1541]( https://github.com/SEED-platform/seed/pull/1541 ), upgrade some dependencies to the latest versions
- Fixed [#1542]( https://github.com/SEED-platform/seed/pull/1542 ), fix serialization of quantity
- Fixed [#1544]( https://github.com/SEED-platform/seed/pull/1544 ), CSV Export Header
- Fixed [#1545]( https://github.com/SEED-platform/seed/pull/1545 ), remove unused view methods and remove bricr flipper
- Fixed [#1546]( https://github.com/SEED-platform/seed/pull/1546 ), Add Sentry to Frontend

Accepted External Pull Requests: 6
- Fixed [#1492]( https://github.com/SEED-platform/seed/pull/1492 ), OGBS - French (Canada) localization
- Fixed [#1514]( https://github.com/SEED-platform/seed/pull/1514 ), Simplify API auth docs
- Fixed [#1516]( https://github.com/SEED-platform/seed/pull/1516 ), HPXML Integration
- Fixed [#1518]( https://github.com/SEED-platform/seed/pull/1518 ), Tightens up check for whether celery's running in dev
- Fixed [#1522]( https://github.com/SEED-platform/seed/pull/1522 ), Fixes HTML error in sub-org submit button
- Fixed [#1537]( https://github.com/SEED-platform/seed/pull/1537 ), Re-sorts angular localization files

# SEED Version 2.2.1

Closed Issues: 5
- Fixed [#1486]( https://github.com/SEED-platform/seed/pull/1486 ), Upgrade to Django 1.11
- Fixed [#1502]( https://github.com/SEED-platform/seed/pull/1502 ), Fix password reset
- Fixed [#1363]( https://github.com/SEED-platform/seed/issues/1363 ), DQ Check - Add export to Inventory DQ Results modal
- Fixed [#1397]( https://github.com/SEED-platform/seed/issues/1397 ), DQ Admin: add indication of field source (tax lot or property)
- Fixed [#1398]( https://github.com/SEED-platform/seed/issues/1398 ), DQ: Add labels for exported records
- Fixed [#1404]( https://github.com/SEED-platform/seed/issues/1404 ), Inventory Detail - Related Properties - need to display more fields
- Fixed [#1439]( https://github.com/SEED-platform/seed/issues/1439 ), Strftime fails for buildings older than 1900
- Fixed [#1496]( https://github.com/SEED-platform/seed/pull/1496 ), Export data from inventory (including labels)
- Fixed [#1482]( https://github.com/SEED-platform/seed/pull/1482 ), Remove the concept of projects
- Fixed [#1483]( https://github.com/SEED-platform/seed/pull/1483 ), Added `Custom ID 1` field for Related Properties
- Fixed [#1484]( https://github.com/SEED-platform/seed/pull/1484 ), Added a mapping button to `Map SEED fields to imported file fields`
- Fixed [#1481]( https://github.com/SEED-platform/seed/pull/1481 ), Hides `*_pint` columns in Property List Settings view
- Fixed [#1487]( https://github.com/SEED-platform/seed/pull/1487 ), Improved Column Saving
- Fixed [#1490]( https://github.com/SEED-platform/seed/pull/1490 ), Export DQ from Inventory
- Fixed [#1493]( https://github.com/SEED-platform/seed/pull/1493 ), Removes node_modules from fine-uploader after building
- Fixed [#1473]( https://github.com/SEED-platform/seed/pull/1473 ), Improved Angular unit tests
- Fixed [#1479]( https://github.com/SEED-platform/seed/pull/1479 ), Disable all client-side caching when the dev profile is used

# SEED Version 2.2

Closed Issues: 25
- Fixed [#558]( https://github.com/SEED-platform/seed/issues/558 ), Label pulldown gets too small to read label text when browser window shrinks
- Fixed [#598]( https://github.com/SEED-platform/seed/issues/598 ), Adding a label to 16,000+ records is a bit slow
- Fixed [#781]( https://github.com/SEED-platform/seed/issues/781 ), Mapping hangs if there is a duplicate field name in the data
- Fixed [#908]( https://github.com/SEED-platform/seed/issues/908 ), Changing the name of the label currently being filtered on
- Fixed [#928]( https://github.com/SEED-platform/seed/issues/928 ), Blank field name in imported file causes error
- Fixed [#1144]( https://github.com/SEED-platform/seed/issues/1144 ), Mapping Review Screen: View by Property tab displays when mapped Tax Lot file has Jurisdiction Tax Lot ID
- Fixed [#1219]( https://github.com/SEED-platform/seed/issues/1219 ), One property record added when only tax lot data is mapped
- Fixed [#1239]( https://github.com/SEED-platform/seed/issues/1239 ), Mapping Review screen doesn't always show data
- Fixed [#1257]( https://github.com/SEED-platform/seed/issues/1257 ), Field name with apostrophe capitalized the next character
- Fixed [#1269]( https://github.com/SEED-platform/seed/issues/1269 ), Check Matching results screen to make sure information is correct
- Fixed [#1275]( https://github.com/SEED-platform/seed/issues/1275 ), Save Mapping for PM file with lots of fields -- Browser unresponsive message
- Fixed [#1280]( https://github.com/SEED-platform/seed/issues/1280 ), Not all fields show data in Mapping Review but are in Inventory list
- Fixed [#1283]( https://github.com/SEED-platform/seed/issues/1283 ), View by Property: Address Line 1 (tax lot) doesn't display unless Address Line 1 (property) is also selected
- Fixed [#1311]( https://github.com/SEED-platform/seed/issues/1311 ), Matching Results dialog box -- make the information there more informative for the user
- Fixed [#1312]( https://github.com/SEED-platform/seed/issues/1312 ), Hand Matching screen -- keep "state" going from detail back to list
- Fixed [#1320]( https://github.com/SEED-platform/seed/issues/1320 ), Display Names in List Settings not always displayed
- Fixed [#1323]( https://github.com/SEED-platform/seed/issues/1323 ), Spinner needs to spin longer (!) before matching screen is displayed
- Fixed [#1329]( https://github.com/SEED-platform/seed/issues/1329 ), Normalization of Tax lot ID -- may cause problems for some cases
- Fixed [#1347]( https://github.com/SEED-platform/seed/issues/1347 ),  502 Bad Gateway area when matching Portfolio Manager file
- Fixed [#1372]( https://github.com/SEED-platform/seed/issues/1372 ), Import sample data issue
- Fixed [#1387]( https://github.com/SEED-platform/seed/issues/1387 ), DQ Check -- Optimize checking for large datasets
- Fixed [#1394]( https://github.com/SEED-platform/seed/issues/1394 ), Matching List and Detail View -- Add List Settings
- Fixed [#1407]( https://github.com/SEED-platform/seed/issues/1407 ), Matching -- sorting takes a while, need a spinner
- Fixed [#1432]( https://github.com/SEED-platform/seed/issues/1432 ), Add fields (list settings) to Pairing screen - can't see enough info to do the pairing
- Fixed [#1470]( https://github.com/SEED-platform/seed/issues/1470 ), Can't create new user from admin page

Accepted External Pull Requests: 7
- Fixed [#978]( https://github.com/SEED-platform/seed/pull/978 ), Adding ansible provisioning within AWS
- Fixed [#1304]( https://github.com/SEED-platform/seed/pull/1304 ), WIP: 1124 linux installation docs
- Fixed [#1440]( https://github.com/SEED-platform/seed/pull/1440 ), Org-level units preference
- Fixed [#1443]( https://github.com/SEED-platform/seed/pull/1443 ), Makes start-seed run a bit easier under Vagrant
- Fixed [#1453]( https://github.com/SEED-platform/seed/pull/1453 ), Fix typo, remove spurious 301 redirect.
- Fixed [#1454]( https://github.com/SEED-platform/seed/pull/1454 ), Fixes startup warning on `seed.NonCanonicalProjectBuildings.projectbuilding`
- Fixed [#1457]( https://github.com/SEED-platform/seed/pull/1457 ), Lay foundations for `pint` Quantity objects for EUI, Areas on PropertyStates

# SEED Version 2.1.2

Closed Issues: 11
- Fixed [#1220]( https://github.com/SEED-platform/seed/issues/1220 ), Hide Column doesn't persist state in List View, only when set in List Settings
- Fixed [#1224]( https://github.com/SEED-platform/seed/issues/1224 ), List Settings are not saved after closing and reopening browser
- Fixed [#1242]( https://github.com/SEED-platform/seed/issues/1242 ), Add a clear filters button to the Inventory List view
- Fixed [#1291]( https://github.com/SEED-platform/seed/issues/1291 ), Save Changes does not appear to work in Detail View
- Fixed [#1341]( https://github.com/SEED-platform/seed/issues/1341 ), Check for duplicate records on import and don't import them
- Fixed [#1395]( https://github.com/SEED-platform/seed/issues/1395 ), Matching List view - add filter line
- Fixed [#1401]( https://github.com/SEED-platform/seed/issues/1401 ), Add a Not "Label" option to filtering
- Fixed [#1410]( https://github.com/SEED-platform/seed/issues/1410 ), Filtering in PM Property ID field doesn't do "contains" filter
- Fixed [#1416]( https://github.com/SEED-platform/seed/issues/1416 ), Can't filter on dates using operators
- Fixed [#1418]( https://github.com/SEED-platform/seed/issues/1418 ), Date sometimes does not display correctly in the Detail view
- Fixed [#1428]( https://github.com/SEED-platform/seed/issues/1428 ), Add Pagination to Matching Detail View

Accepted External Pull Requests: 0

# SEED Version 2.1.1

Closed Issues: 77
- Fixed [#16]( https://github.com/SEED-platform/seed/issues/16 ), Clear Type ahead history and restart with clean default list
- Fixed [#18]( https://github.com/SEED-platform/seed/issues/18 ), Admin function to change % confidence setting
- Fixed [#47]( https://github.com/SEED-platform/seed/issues/47 ), Fix case sensitive sort in Mapping edit column
- Fixed [#53]( https://github.com/SEED-platform/seed/issues/53 ), Save intermediate state of mapping
- Fixed [#54]( https://github.com/SEED-platform/seed/issues/54 ), The same user can be added to an organization multiple times
- Fixed [#101]( https://github.com/SEED-platform/seed/issues/101 ), MATCHING: Sorting by confidence across entire dataset
- Fixed [#133]( https://github.com/SEED-platform/seed/issues/133 ), Edit Columns in mapping -- only show fields in the dataset currently being mapped
- Fixed [#199]( https://github.com/SEED-platform/seed/issues/199 ), PM JSON mapping field doesn't handle case (?)
- Fixed [#213]( https://github.com/SEED-platform/seed/issues/213 ), Case sensitivity in mapping
- Fixed [#231]( https://github.com/SEED-platform/seed/issues/231 ), Filter parameters being saved
- Fixed [#271]( https://github.com/SEED-platform/seed/issues/271 ), Address sort -- alpha sort on street number (?)
- Fixed [#272]( https://github.com/SEED-platform/seed/issues/272 ), Client-side build tool?
- Fixed [#277]( https://github.com/SEED-platform/seed/issues/277 ), SEED incorrectly sees Firefox on OSX as old version
- Fixed [#278]( https://github.com/SEED-platform/seed/issues/278 ), Modal dialogs should not show dismissable alerts
- Fixed [#280]( https://github.com/SEED-platform/seed/issues/280 ), Dropdowns are not auto-showing scrollbars
- Fixed [#283]( https://github.com/SEED-platform/seed/issues/283 ), Use standard (Bootstrap) modal dialog for delete project and delete data set
- Fixed [#284]( https://github.com/SEED-platform/seed/issues/284 ), Use better label for "Successful Upload!" dialog
- Fixed [#298]( https://github.com/SEED-platform/seed/issues/298 ), Missing asset: bg_first_td.png
- Fixed [#321]( https://github.com/SEED-platform/seed/issues/321 ), List Settings in Building View has case sensitive sort
- Fixed [#322]( https://github.com/SEED-platform/seed/issues/322 ), Field name display inconsistencies
- Fixed [#350]( https://github.com/SEED-platform/seed/issues/350 ), Creating Sub Orgs seems to be broken
- Fixed [#357]( https://github.com/SEED-platform/seed/issues/357 ), Deleting Building snapshot records when deleting data sets
- Fixed [#363]( https://github.com/SEED-platform/seed/issues/363 ), missing backgound image
- Fixed [#371]( https://github.com/SEED-platform/seed/issues/371 ), Duplicates in matching using PM web services field names
- Fixed [#431]( https://github.com/SEED-platform/seed/issues/431 ), Delete records when click "Back to Mapping"
- Fixed [#439]( https://github.com/SEED-platform/seed/issues/439 ), Mapping -- storing mapping results in cache
- Fixed [#443]( https://github.com/SEED-platform/seed/issues/443 ), Add JS tests to travis build
- Fixed [#450]( https://github.com/SEED-platform/seed/issues/450 ), 403 error posting to /data/upload/
- Fixed [#455]( https://github.com/SEED-platform/seed/issues/455 ), Remove javascript:void(0); in href tags
- Fixed [#498]( https://github.com/SEED-platform/seed/issues/498 ), Expand filtering to include multiple criteria
- Fixed [#529]( https://github.com/SEED-platform/seed/issues/529 ), Fix outdated browser code
- Fixed [#552]( https://github.com/SEED-platform/seed/issues/552 ), Label filter should be case insensitive
- Fixed [#570]( https://github.com/SEED-platform/seed/issues/570 ), Address *debt* related to building search
- Fixed [#588]( https://github.com/SEED-platform/seed/issues/588 ), /static/landing/js/landing.js missing
- Fixed [#603]( https://github.com/SEED-platform/seed/issues/603 ), AttributeError: 'int' object has no attribute 'strip'
- Fixed [#625]( https://github.com/SEED-platform/seed/issues/625 ), Add javascript tests to Travis-CI
- Fixed [#637]( https://github.com/SEED-platform/seed/issues/637 ), Small correction needed for comments
- Fixed [#641]( https://github.com/SEED-platform/seed/issues/641 ), Refactor directive names
- Fixed [#658]( https://github.com/SEED-platform/seed/issues/658 ), Number of matching records seems to depend on import order
- Fixed [#666]( https://github.com/SEED-platform/seed/issues/666 ), Font in Log and Notes Action field has changed
- Fixed [#682]( https://github.com/SEED-platform/seed/issues/682 ), Add more help text for Cancel button on Confirm Save Mappings modal
- Fixed [#691]( https://github.com/SEED-platform/seed/issues/691 ), Program doesn't allow mapping even if duplicate fields are unchecked
- Fixed [#698]( https://github.com/SEED-platform/seed/issues/698 ), Add column sorting to detailed matching screen
- Fixed [#813]( https://github.com/SEED-platform/seed/issues/813 ), Matching shows 0% progress, but is actually matching (on a large dataset)
- Fixed [#814]( https://github.com/SEED-platform/seed/issues/814 ), Matching design issues
- Fixed [#828]( https://github.com/SEED-platform/seed/issues/828 ), 2nd step in Mapping seems to either hang or take a very long time
- Fixed [#852]( https://github.com/SEED-platform/seed/issues/852 ), Uploading large data set, problem with matching
- Fixed [#872]( https://github.com/SEED-platform/seed/issues/872 ), Display of files is slow if the list of files is long
- Fixed [#886]( https://github.com/SEED-platform/seed/issues/886 ), UI Updates for DB Refactoring
- Fixed [#907]( https://github.com/SEED-platform/seed/issues/907 ), After applying labels on page > 1, program goes back to showing page 1 list
- Fixed [#911]( https://github.com/SEED-platform/seed/issues/911 ), local_untracked has changed
- Fixed [#954]( https://github.com/SEED-platform/seed/issues/954 ), Fix Django deprecated warnings.
- Fixed [#975]( https://github.com/SEED-platform/seed/issues/975 ), Data migration to put extra data fields into column mappings
- Fixed [#1022]( https://github.com/SEED-platform/seed/issues/1022 ), Cancel button on Change Password page appears to have no effect
- Fixed [#1072]( https://github.com/SEED-platform/seed/issues/1072 ), Filter by label state is lost going from list to detail and back to list
- Fixed [#1141]( https://github.com/SEED-platform/seed/issues/1141 ), Inventory List: put multiple tax lots in numeric order
- Fixed [#1143]( https://github.com/SEED-platform/seed/issues/1143 ), Problems with Matching
- Fixed [#1162]( https://github.com/SEED-platform/seed/issues/1162 ), Keep sort & filter when coming back to List view from Detail View
- Fixed [#1208]( https://github.com/SEED-platform/seed/issues/1208 ), Jurisdiction Property ID -- add it to the list of matching fields
- Fixed [#1218]( https://github.com/SEED-platform/seed/issues/1218 ), Extra Data sorting -- should sort all fields alpha-numerically (?)
- Fixed [#1222]( https://github.com/SEED-platform/seed/issues/1222 ), Add ability to Set Campus field state in Detail Edit
- Fixed [#1228]( https://github.com/SEED-platform/seed/issues/1228 ), Need funtionality equivalent to "Lot Number" in PM data for Unique Building ID in PM data
- Fixed [#1247]( https://github.com/SEED-platform/seed/issues/1247 ), Don't merge duplicate records
- Fixed [#1255]( https://github.com/SEED-platform/seed/issues/1255 ), After mapping is saved, some fields are set to unmapped in the Mapping Screen
- Fixed [#1258]( https://github.com/SEED-platform/seed/issues/1258 ), Verify the behavior of mapping Tax Lot ID to Lot Number if Tax Lot ID doesn't exist in Tax Lot table
- Fixed [#1267]( https://github.com/SEED-platform/seed/issues/1267 ), Enable Django File Compression for Cache Busting
- Fixed [#1276]( https://github.com/SEED-platform/seed/issues/1276 ), Error running docker-compose
- Fixed [#1279]( https://github.com/SEED-platform/seed/issues/1279 ), Manage Available cycles -- doesn't always work
- Fixed [#1288]( https://github.com/SEED-platform/seed/issues/1288 ), Recognize / as a delimiter for multiple tax lot IDs
- Fixed [#1300]( https://github.com/SEED-platform/seed/issues/1300 ), Hand matching: Spinner needs to persist until hand matching view is displayed
- Fixed [#1313]( https://github.com/SEED-platform/seed/issues/1313 ), UI for cases where multiple records are matched -- improve
- Fixed [#1334]( https://github.com/SEED-platform/seed/issues/1334 ), If field order is changed by moving field in list view, when coming back from detail view, list settings are lost
- Fixed [#1368]( https://github.com/SEED-platform/seed/issues/1368 ), DQ check - getting errors for Address Line 1 even if it isn't in the rules
- Fixed [#1376]( https://github.com/SEED-platform/seed/issues/1376 ), Hand matching is very slow
- Fixed [#1383]( https://github.com/SEED-platform/seed/issues/1383 ), Matching list and detail view -- add back in column filtering and field list settings (in V 1.5)
- Fixed [#1384]( https://github.com/SEED-platform/seed/issues/1384 ), Matching detail list -- add column sorting (like the list view)
- Fixed [#1412]( https://github.com/SEED-platform/seed/issues/1412 ), Blank data in matching fields causes records to be merged that shouldn't be

Accepted External Pull Requests: 12
- Fixed [#1199]( https://github.com/SEED-platform/seed/pull/1199 ), Basic authentication uses base64 encoded, not plain strings
- Fixed [#1241]( https://github.com/SEED-platform/seed/pull/1241 ), Fixes Python build failures in Docker
- Fixed [#1366]( https://github.com/SEED-platform/seed/pull/1366 ), Tests data quality
- Fixed [#1373]( https://github.com/SEED-platform/seed/pull/1373 ), Fix develop tests
- Fixed [#1378]( https://github.com/SEED-platform/seed/pull/1378 ), GBR merge 01 residential cert models
- Fixed [#1379]( https://github.com/SEED-platform/seed/pull/1379 ), GBR merge 02 api helpers
- Fixed [#1381]( https://github.com/SEED-platform/seed/pull/1381 ), GBR merge 03 residential cert endpoints
- Fixed [#1382]( https://github.com/SEED-platform/seed/pull/1382 ), GBR merge 04 a org mixin cycle
- Fixed [#1386]( https://github.com/SEED-platform/seed/pull/1386 ), Filter matching
- Fixed [#1388]( https://github.com/SEED-platform/seed/pull/1388 ), 90 code cov
- Fixed [#1389]( https://github.com/SEED-platform/seed/pull/1389 ), GBR merge 05 properties

# SEED Version 2.1.0

Closed Issues: 29
- Fixed [#69]( https://github.com/SEED-platform/seed/issues/69 ), Remember the unchecked fields
- Fixed [#79]( https://github.com/SEED-platform/seed/issues/79 ), Separate Mapping from Matching
- Fixed [#430]( https://github.com/SEED-platform/seed/issues/430 ), Potential crash in map_row_chunk
- Fixed [#580]( https://github.com/SEED-platform/seed/issues/580 ), Add Label Feature to Data Cleansing view
- Fixed [#582]( https://github.com/SEED-platform/seed/issues/582 ), Add Data Cleansing functionality to Inventory (Property and Tax Lot) View
- Fixed [#785]( https://github.com/SEED-platform/seed/issues/785 ), Add Clear Filter to Data Cleansing modal
- Fixed [#787]( https://github.com/SEED-platform/seed/issues/787 ), Additional functionality to add to Data Cleansing Admin feature
- Fixed [#1105]( https://github.com/SEED-platform/seed/issues/1105 ), Slow display of data
- Fixed [#1151]( https://github.com/SEED-platform/seed/issues/1151 ), Mapping for PM files need some improvement
- Fixed [#1171]( https://github.com/SEED-platform/seed/issues/1171 ), List Settings - Multiple field names still there in some cases
- Fixed [#1236]( https://github.com/SEED-platform/seed/issues/1236 ), Is `seed-platform-dev` google group dead?
- Fixed [#1243]( https://github.com/SEED-platform/seed/issues/1243 ), Dismiss button on Matching Progress bar
- Fixed [#1274]( https://github.com/SEED-platform/seed/issues/1274 ), Deleting organizations doesn't seem to work -- Disable until fixed
- Fixed [#1287]( https://github.com/SEED-platform/seed/issues/1287 ), Data Cleansing Export button doesn't export file
- Fixed [#1307]( https://github.com/SEED-platform/seed/issues/1307 ), Chrome ran out of memory trying to display the matching screen
- Fixed [#1309]( https://github.com/SEED-platform/seed/issues/1309 ), Error unmerging merged record
- Fixed [#1324]( https://github.com/SEED-platform/seed/issues/1324 ), Mapping Review only shows Tax Lot field if Address Line 1 mapped to Property table
- Fixed [#1342]( https://github.com/SEED-platform/seed/issues/1342 ), Keep Label filters when moving between tabs
- Fixed [#1343]( https://github.com/SEED-platform/seed/issues/1343 ), 500 Error when clicking on Data Quality Checks from right hand link in organizations
- Fixed [#1345]( https://github.com/SEED-platform/seed/issues/1345 ), DQ checking -- put new rule at top of list
- Fixed [#1346]( https://github.com/SEED-platform/seed/issues/1346 ), DQ Checking -- Not all rules are alphabetized
- Fixed [#1350]( https://github.com/SEED-platform/seed/issues/1350 ), DQ - Text String checking
- Fixed [#1351]( https://github.com/SEED-platform/seed/issues/1351 ), DQ - Select / Deselect All button in DQ Admin
- Fixed [#1352]( https://github.com/SEED-platform/seed/issues/1352 ), DQ - Default rules for Energy Star seem to hang (?)
- Fixed [#1353]( https://github.com/SEED-platform/seed/issues/1353 ), DQ - Energy Star Score rule seems to hang (?)
- Fixed [#1354]( https://github.com/SEED-platform/seed/issues/1354 ), DQ Check - Program doesn't label null records when set to Required and Not Null
- Fixed [#1355]( https://github.com/SEED-platform/seed/issues/1355 ), DQ Check -- Alphabetize field list in field pulldown in Admin Screen
- Fixed [#1359]( https://github.com/SEED-platform/seed/issues/1359 ), DQ Check -- Error adding labels in Admin Screen
- Fixed [#1364]( https://github.com/SEED-platform/seed/issues/1364 ), DQ - Not all error records are getting labels

Accepted External Pull Requests: 2
- Fixed [#1331]( https://github.com/SEED-platform/seed/pull/1331 ), Old data quality
- Fixed [#1333]( https://github.com/SEED-platform/seed/pull/1333 ), Cleanup

# SEED Version 2.0.2

Closed Issues: 49
- Fixed [#23]( https://github.com/SEED-platform/seed/issues/23 ), Type ahead in Mapping sometimes doesn’t keep your choice
- Fixed [#82]( https://github.com/SEED-platform/seed/issues/82 ), Batch processing during import causes lost records
- Fixed [#103]( https://github.com/SEED-platform/seed/issues/103 ), Improving the mapping functionality
- Fixed [#122]( https://github.com/SEED-platform/seed/issues/122 ), Linked fields in Mapping
- Fixed [#149]( https://github.com/SEED-platform/seed/issues/149 ), Click on field or record to edit
- Fixed [#370]( https://github.com/SEED-platform/seed/issues/370 ), Move Filtering and Sorting to Front End
- Fixed [#462]( https://github.com/SEED-platform/seed/issues/462 ), Add wildcards to filtering
- Fixed [#518]( https://github.com/SEED-platform/seed/issues/518 ), Server error on Delete Building
- Fixed [#542]( https://github.com/SEED-platform/seed/issues/542 ), Changes to PM mapping not shown in mapping "review" screen after save
- Fixed [#620]( https://github.com/SEED-platform/seed/issues/620 ), Wrong number of matched buildings reported in dialog box
- Fixed [#633]( https://github.com/SEED-platform/seed/issues/633 ), Program Doesn't Always show the right number of matches
- Fixed [#643]( https://github.com/SEED-platform/seed/issues/643 ), Add double date filters to matching screen
- Fixed [#657]( https://github.com/SEED-platform/seed/issues/657 ), Number of matches reported in modal is not always correct
- Fixed [#659]( https://github.com/SEED-platform/seed/issues/659 ), Add/Remove filter buttons stacked not side by side
- Fixed [#661]( https://github.com/SEED-platform/seed/issues/661 ), Add/Remove filter buttons stacked not side by side
- Fixed [#665]( https://github.com/SEED-platform/seed/issues/665 ), Deleting buildings from list doesn't delete all records
- Fixed [#827]( https://github.com/SEED-platform/seed/issues/827 ), Program renames data import file
- Fixed [#874]( https://github.com/SEED-platform/seed/issues/874 ), Save GreenButton Request button doesn't save deletion of input in URL and Subscription fields
- Fixed [#931]( https://github.com/SEED-platform/seed/issues/931 ), API Refactoring
- Fixed [#933]( https://github.com/SEED-platform/seed/issues/933 ), Build Migration Scripts to move data from old to new tables
- Fixed [#953]( https://github.com/SEED-platform/seed/issues/953 ), Edited data in Building Detail view is not saved
- Fixed [#980]( https://github.com/SEED-platform/seed/issues/980 ), Imported files have a sequential number appended onto them
- Fixed [#1107]( https://github.com/SEED-platform/seed/issues/1107 ), Program merges records during matching if addresses match but Tax Lot IDs are different
- Fixed [#1108]( https://github.com/SEED-platform/seed/issues/1108 ), Program doesn't handle updated PM records in the same file properly
- Fixed [#1112]( https://github.com/SEED-platform/seed/issues/1112 ), Matching hangs importing the same file under 2 different cycles
- Fixed [#1139]( https://github.com/SEED-platform/seed/issues/1139 ), Show import history in the Inventory Detail view
- Fixed [#1159]( https://github.com/SEED-platform/seed/issues/1159 ), Getting Bower errors matching data
- Fixed [#1203]( https://github.com/SEED-platform/seed/issues/1203 ), Changing mapping doesn't seem to get saved
- Fixed [#1206]( https://github.com/SEED-platform/seed/issues/1206 ), Mapping to Lot Number -- can't view Lot Number field explicitly - it becomes Associated Tax Lot ID (?)
- Fixed [#1207]( https://github.com/SEED-platform/seed/issues/1207 ), Mapping error checking -- require at least one field is a matching field
- Fixed [#1215]( https://github.com/SEED-platform/seed/issues/1215 ), Display of mapping list is very slow when there are many fields (250)
- Fixed [#1221]( https://github.com/SEED-platform/seed/issues/1221 ), Replicate V1.5 feedback for matching results
- Fixed [#1259]( https://github.com/SEED-platform/seed/issues/1259 ), No fields displaying in Mapping Review
- Fixed [#1261]( https://github.com/SEED-platform/seed/issues/1261 ), Settings not saved on Detail View
- Fixed [#1262]( https://github.com/SEED-platform/seed/issues/1262 ), Data doesn't always appear in Mapping Review, even if it is displayed in Inventory view
- Fixed [#1263]( https://github.com/SEED-platform/seed/issues/1263 ), A few mapped Tax Lot fields are not showing data in the Property List view (City, State, Postal Code)
- Fixed [#1264]( https://github.com/SEED-platform/seed/issues/1264 ), Test and Document -- Mapping Lot Number to Property in file with both Tax Lot and Property Data
- Fixed [#1278]( https://github.com/SEED-platform/seed/issues/1278 ), How to unpair a Property from a Tax Lot
- Fixed [#1285]( https://github.com/SEED-platform/seed/issues/1285 ), Problem importing 2 records with fields mapped to Tax Lot and Properties
- Fixed [#1290]( https://github.com/SEED-platform/seed/issues/1290 ), Mapping error: Cannot handle more than one to_column returned for <fieldname>
- Fixed [#1293]( https://github.com/SEED-platform/seed/issues/1293 ), Detail View error -- 'NoneType' object has no attribute 'state'
- Fixed [#1294]( https://github.com/SEED-platform/seed/issues/1294 ), Timeout viewing detail from View by Tax Lot
- Fixed [#1295]( https://github.com/SEED-platform/seed/issues/1295 ), Importing 2nd file -- no data displayed in Matching Review
- Fixed [#1299]( https://github.com/SEED-platform/seed/issues/1299 ), Mapping to Lot Number in Property table -- normalize data the same way as for Jurisdiction Tax Lot ID
- Fixed [#1305]( https://github.com/SEED-platform/seed/issues/1305 ), Program defaults to "empty" Cycle record in Inventory view
- Fixed [#1306]( https://github.com/SEED-platform/seed/issues/1306 ), Server error 500 clicking on Detail icon from View by Property, 502 from View by Tax Lot
- Fixed [#1308]( https://github.com/SEED-platform/seed/issues/1308 ), 1 Portfolio Manager record not getting added to Property list
- Fixed [#1310]( https://github.com/SEED-platform/seed/issues/1310 ), Program seems to stall on Mapping
- Fixed [#1315]( https://github.com/SEED-platform/seed/issues/1315 ), Manage Available Cycles on New Data Set not working

Accepted External Pull Requests: 3
- Fixed [#1284]( https://github.com/SEED-platform/seed/pull/1284 ), Seed merge api helpers
- Fixed [#1286]( https://github.com/SEED-platform/seed/pull/1286 ), fix for pairing page, didn't like scope() syntax
- Fixed [#1322]( https://github.com/SEED-platform/seed/pull/1322 ), 135787765 test updates

# SEED Version 2.0.1

Closed Issues: 18
- Fixed [#138]( https://github.com/SEED-platform/seed/issues/138 ), Add cancel button to data import modal
- Fixed [#618]( https://github.com/SEED-platform/seed/issues/618 ), Decouple list settings in different views
- Fixed [#632]( https://github.com/SEED-platform/seed/issues/632 ), Add Cancel button to View/Hide Columns / Save Settings on Matching screen
- Fixed [#650]( https://github.com/SEED-platform/seed/issues/650 ), Year built displayed with commas in matching
- Fixed [#871]( https://github.com/SEED-platform/seed/issues/871 ), Add date/time of import for uploaded files in the Data Files section
- Fixed [#910]( https://github.com/SEED-platform/seed/issues/910 ), Update filtering in the Matching detail view
- Fixed [#1007]( https://github.com/SEED-platform/seed/issues/1007 ), DB Migration cleanup -- DC and 2015-2016
- Fixed [#1087]( https://github.com/SEED-platform/seed/issues/1087 ), List settings contains multiple versions of the same field -- don't know which to pick
- Fixed [#1118]( https://github.com/SEED-platform/seed/issues/1118 ), Imported files don't always show extension
- Fixed [#1128]( https://github.com/SEED-platform/seed/issues/1128 ), Matching with Tax Lot & Property Data in one file
- Fixed [#1165]( https://github.com/SEED-platform/seed/issues/1165 ), Saved mapping is not always correct
- Fixed [#1168]( https://github.com/SEED-platform/seed/issues/1168 ), In existing org, importing new files, Mapping Review screen doesn't show data
- Fixed [#1170]( https://github.com/SEED-platform/seed/issues/1170 ), List Settings: Property and Tax Lot indicators are not always correct, depending on the mapping
- Fixed [#1178]( https://github.com/SEED-platform/seed/issues/1178 ), Detail Settings (both Tax Lot and Property) doesn't show extra data fields
- Fixed [#1183]( https://github.com/SEED-platform/seed/issues/1183 ), Extra Data doesn't display in Inventory List or Detail View
- Fixed [#1204]( https://github.com/SEED-platform/seed/issues/1204 ), Custom ID 1 is not displayed in Mapping Review or Property List Settings
- Fixed [#1213]( https://github.com/SEED-platform/seed/issues/1213 ), Some data getting mapped is not displaying in detail and list view
- Fixed [#1217]( https://github.com/SEED-platform/seed/issues/1217 ), 403 Forbidden Error in matching_results

Accepted External Pull Requests: 2
- Fixed [#1135]( https://github.com/SEED-platform/seed/pull/1135 ), Import changes
- Fixed [#1253]( https://github.com/SEED-platform/seed/pull/1253 ), added taxlot_view_id to related property returned in getProperties

# SEED Version 2.0.0 (2016-10-01 to Release)

Closed Issues: 76
- Fixed [#78]( https://github.com/SEED-platform/seed/issues/78 ), MATCHING: Unmatched PM records are not made into master building records
- Fixed [#98]( https://github.com/SEED-platform/seed/issues/98 ), Concatenation isn't working -- can't control field order
- Fixed [#110]( https://github.com/SEED-platform/seed/issues/110 ), Address Line 1 mapping not working
- Fixed [#114]( https://github.com/SEED-platform/seed/issues/114 ), Scale building list records viewed based on total # of records
- Fixed [#248]( https://github.com/SEED-platform/seed/issues/248 ), Problem deleting buildings
- Fixed [#314]( https://github.com/SEED-platform/seed/issues/314 ), "File Content Error" during data load but system still loads data
- Fixed [#397]( https://github.com/SEED-platform/seed/issues/397 ), Display error message when creating label if it already exists
- Fixed [#407]( https://github.com/SEED-platform/seed/issues/407 ), Order of fields in Building List for existing records
- Fixed [#420]( https://github.com/SEED-platform/seed/issues/420 ), Put display # records pull down at the top of the list
- Fixed [#585]( https://github.com/SEED-platform/seed/issues/585 ), If no matching fields mapped, can't get to Building Details
- Fixed [#587]( https://github.com/SEED-platform/seed/issues/587 ), Missing {{STATIC_URL}}seed/images/DOE-SEED-Logo_v4.jpg
- Fixed [#597]( https://github.com/SEED-platform/seed/issues/597 ), Labels take a long time to load if there is a lot of data
- Fixed [#906]( https://github.com/SEED-platform/seed/issues/906 ), Clear filters goes back to Show All state, but pulldown doesn't reflect that state
- Fixed [#917]( https://github.com/SEED-platform/seed/issues/917 ), Label list doesn't appear on first click into the input box
- Fixed [#967]( https://github.com/SEED-platform/seed/issues/967 ), Sentry errors from trying to display building list
- Fixed [#971]( https://github.com/SEED-platform/seed/issues/971 ), Error mapping
- Fixed [#973]( https://github.com/SEED-platform/seed/issues/973 ), Unchecked fields in Mapping screen are imported but not available in Building List Settings #972
- Fixed [#984]( https://github.com/SEED-platform/seed/issues/984 ), In superuser organization list (under Admin) show the Organization ID from the database in a column
- Fixed [#990]( https://github.com/SEED-platform/seed/issues/990 ), Can't export just one record
- Fixed [#991]( https://github.com/SEED-platform/seed/issues/991 ), Investigate sentry errors
- Fixed [#999]( https://github.com/SEED-platform/seed/issues/999 ), Add Associated Tax Lots to UI for new db refactoring
- Fixed [#1000]( https://github.com/SEED-platform/seed/issues/1000 ), Angular Grid UI - Add field display on/off, persistence of UI state
- Fixed [#1010]( https://github.com/SEED-platform/seed/issues/1010 ), Table layout inconsistencies
- Fixed [#1030]( https://github.com/SEED-platform/seed/issues/1030 ), import file into new data model
- Fixed [#1031]( https://github.com/SEED-platform/seed/issues/1031 ), Investigate Sentry error
- Fixed [#1033]( https://github.com/SEED-platform/seed/issues/1033 ), Add link to Swagger on front end
- Fixed [#1049]( https://github.com/SEED-platform/seed/issues/1049 ), Testing filtering in Blue Sky
- Fixed [#1084]( https://github.com/SEED-platform/seed/issues/1084 ), Mapping grid only shows extra data and no data for the records
- Fixed [#1085]( https://github.com/SEED-platform/seed/issues/1085 ), Duplicate Fields in Mapping -- can't assign them to a Tax Lot or Property table
- Fixed [#1086]( https://github.com/SEED-platform/seed/issues/1086 ), Program doesn't save "state" of mapping after saving (the table assigned to the field)
- Fixed [#1089]( https://github.com/SEED-platform/seed/issues/1089 ), Not all records imported into View by Property
- Fixed [#1090]( https://github.com/SEED-platform/seed/issues/1090 ), Program automatically creates duplicate mapping even though the original fields names are unique
- Fixed [#1091]( https://github.com/SEED-platform/seed/issues/1091 ), Import, Map and Match Sample Data - Record Pairing doesn't seem to be working
- Fixed [#1092]( https://github.com/SEED-platform/seed/issues/1092 ), Mapping for some fields is changed in the List view
- Fixed [#1094]( https://github.com/SEED-platform/seed/issues/1094 ), Data displayed in Inventory View by Property list is associated with the original field name, not mapped field name
- Fixed [#1095]( https://github.com/SEED-platform/seed/issues/1095 ), Error trying to add label from View by Tax Lot tab
- Fixed [#1096]( https://github.com/SEED-platform/seed/issues/1096 ), Failed to load resource: api/v2/projects/count/?organization_id
- Fixed [#1097]( https://github.com/SEED-platform/seed/issues/1097 ), Importing PM file using Portfolio Manager Tab doesn't work
- Fixed [#1099]( https://github.com/SEED-platform/seed/issues/1099 ), Mapping: Back to Mapping button doesn't seem to work
- Fixed [#1100]( https://github.com/SEED-platform/seed/issues/1100 ), Mapping: extra data fields shown in Mapping Review screen with field name not display name
- Fixed [#1101]( https://github.com/SEED-platform/seed/issues/1101 ), Mapping: Show both Tax Lot and Property fields in Mapping Review screen
- Fixed [#1103]( https://github.com/SEED-platform/seed/issues/1103 ), Mapping Review: only show fields that were mapped
- Fixed [#1104]( https://github.com/SEED-platform/seed/issues/1104 ), Sluggish UI performance
- Fixed [#1110]( https://github.com/SEED-platform/seed/issues/1110 ), Browser runs out of memory displaying large data set
- Fixed [#1111]( https://github.com/SEED-platform/seed/issues/1111 ), Server times out mapping large data set
- Fixed [#1120]( https://github.com/SEED-platform/seed/issues/1120 ), Unicode Error in Address
- Fixed [#1126]( https://github.com/SEED-platform/seed/issues/1126 ), Mapping review screens doesn't display mapped fields properly
- Fixed [#1127]( https://github.com/SEED-platform/seed/issues/1127 ), Error loading page in mapping
- Fixed [#1129]( https://github.com/SEED-platform/seed/issues/1129 ), Not all Property Data is displayed in Tax Lot rolled up view
- Fixed [#1131]( https://github.com/SEED-platform/seed/issues/1131 ), Deleting user gets "unsupported media type" error
- Fixed [#1134]( https://github.com/SEED-platform/seed/issues/1134 ), Importing junction table for Tax Lot and PM Property ID - Relationships not correct
- Fixed [#1138]( https://github.com/SEED-platform/seed/issues/1138 ), Matching -- progress bar doesn't close even though records are all matched and in inventory list
- Fixed [#1146]( https://github.com/SEED-platform/seed/issues/1146 ), Issues with Portfolio Manager File mapping
- Fixed [#1147]( https://github.com/SEED-platform/seed/issues/1147 ), Program allows user to Map Your Data when it has already been merged
- Fixed [#1148]( https://github.com/SEED-platform/seed/issues/1148 ), Mapping error trying to import data
- Fixed [#1149]( https://github.com/SEED-platform/seed/issues/1149 ), 404 error -- buildings_reports_controller.js
- Fixed [#1150]( https://github.com/SEED-platform/seed/issues/1150 ), Change password failing
- Fixed [#1153]( https://github.com/SEED-platform/seed/issues/1153 ), Make sure Portfolio Manager JSON file is completely populated with PM fields
- Fixed [#1161]( https://github.com/SEED-platform/seed/issues/1161 ), 403 Forbidden error on log off
- Fixed [#1163]( https://github.com/SEED-platform/seed/issues/1163 ), Problem uploading data with filesystem mode
- Fixed [#1164]( https://github.com/SEED-platform/seed/issues/1164 ), Mapping for Address Line 1 in Tax Lot is wrong
- Fixed [#1173]( https://github.com/SEED-platform/seed/issues/1173 ), A few field names are getting automatically mapped to another name
- Fixed [#1174]( https://github.com/SEED-platform/seed/issues/1174 ), Can't import a file with only one field
- Fixed [#1176]( https://github.com/SEED-platform/seed/issues/1176 ), Bad Gateway error when trying to add label (upper limit for number of records to add labels to?)
- Fixed [#1177]( https://github.com/SEED-platform/seed/issues/1177 ), List Settings -- dragging fields to change their order doesn't seem to work
- Fixed [#1182]( https://github.com/SEED-platform/seed/issues/1182 ), Can't create new data set for new organization
- Fixed [#1184]( https://github.com/SEED-platform/seed/issues/1184 ), Strange set of characters are appended on to imported filename
- Fixed [#1186]( https://github.com/SEED-platform/seed/issues/1186 ), Reports don't seem to be working
- Fixed [#1187]( https://github.com/SEED-platform/seed/issues/1187 ), Inventory List records don't display the first time the page is loaded - have to change cycles for display
- Fixed [#1189]( https://github.com/SEED-platform/seed/issues/1189 ), Error 415 - Unsupported Media Type -- when trying to delete user in an Organization view
- Fixed [#1193]( https://github.com/SEED-platform/seed/issues/1193 ), 403 Forbidden error trying to make a Cycle in a new org without any Cycles
- Fixed [#1194]( https://github.com/SEED-platform/seed/issues/1194 ), Error trying to edit an existing Cycle
- Fixed [#1195]( https://github.com/SEED-platform/seed/issues/1195 ), When Creating a new cycle, the cycle list disappears until browser is refreshed
- Fixed [#1196]( https://github.com/SEED-platform/seed/issues/1196 ), Importing Property file without Matching fields (?) only shows one record in View by Property
- Fixed [#1210]( https://github.com/SEED-platform/seed/issues/1210 ), All labels are displayed in Detail view, not just the ones associated with the record
- Fixed [#1212]( https://github.com/SEED-platform/seed/issues/1212 ), Removing Labels in Detail view doesn't update the label list for that record

Accepted External Pull Requests: 11
- Fixed [#1041]( https://github.com/SEED-platform/seed/pull/1041 ), Fix for #1031 cut against release 1.5.0
- Fixed [#1042]( https://github.com/SEED-platform/seed/pull/1042 ), Fix for 1035 backported from tallus-selenium-test-836
- Fixed [#1043]( https://github.com/SEED-platform/seed/pull/1043 ), Fix can't delete data in extra_data fields in Building Detail #1027
- Fixed [#1069]( https://github.com/SEED-platform/seed/pull/1069 ), migrate_labels manage command now uses property.labels etc
- Fixed [#1076]( https://github.com/SEED-platform/seed/pull/1076 ), Bugfixes for labels (and tests)
- Fixed [#1080]( https://github.com/SEED-platform/seed/pull/1080 ), New Projects API
- Fixed [#1081]( https://github.com/SEED-platform/seed/pull/1081 ), Column migration bugfix
- Fixed [#1121]( https://github.com/SEED-platform/seed/pull/1121 ), Added models for Green Assessments (Verifications/Certifications)
- Fixed [#1169]( https://github.com/SEED-platform/seed/pull/1169 ), Nyc migration issue dec 2016
- Fixed [#1181]( https://github.com/SEED-platform/seed/pull/1181 ), 135787537 performance updates
- Fixed [#1211]( https://github.com/SEED-platform/seed/pull/1211 ), 134551255 new pairing page


# SEED Version 2.0.0 (2016-06-11 to 2016-10-01)

losed Issues: 21
- Fixed [#30]( https://github.com/SEED-platform/seed/issues/30 ), Multiple Data Files per Building Record
- Fixed [#59]( https://github.com/SEED-platform/seed/issues/59 ), Column Reordering allowed in Matching Edit Columns view
- Fixed [#66]( https://github.com/SEED-platform/seed/issues/66 ), Add Ability to handle multiple years of data
- Fixed [#508]( https://github.com/SEED-platform/seed/issues/508 ), Finish/Polish ReadTheDocs
- Fixed [#760]( https://github.com/SEED-platform/seed/issues/760 ), The last label does not appear in Building List pulldown
- Fixed [#793]( https://github.com/SEED-platform/seed/issues/793 ), Very long data strings should wrap
- Fixed [#836]( https://github.com/SEED-platform/seed/issues/836 ), Stay in the same place in the building list when coming back from building detail
- Fixed [#878]( https://github.com/SEED-platform/seed/issues/878 ), Set up a release server that replicates production with latest updates
- Fixed [#889]( https://github.com/SEED-platform/seed/issues/889 ), Fix migrations from clean db
- Fixed [#959]( https://github.com/SEED-platform/seed/issues/959 ), UI for Blue Sky Test Release in June
- Fixed [#963]( https://github.com/SEED-platform/seed/issues/963 ), Generate list of all fields in extra data
- Fixed [#965]( https://github.com/SEED-platform/seed/issues/965 ), Bar chart section of report not working
- Fixed [#968]( https://github.com/SEED-platform/seed/issues/968 ), Develop field order for Blue Sky test view
- Fixed [#976]( https://github.com/SEED-platform/seed/issues/976 ), simple_modal_service is broken
- Fixed [#979]( https://github.com/SEED-platform/seed/issues/979 ), Specs for UI for DB refactoring
- Fixed [#982]( https://github.com/SEED-platform/seed/issues/982 ), Building Detail Column width control doesn't work properly in IE
- Fixed [#989]( https://github.com/SEED-platform/seed/issues/989 ), List of labels in building list is not showing all the labels
- Fixed [#998]( https://github.com/SEED-platform/seed/issues/998 ), UI Grid interface for choosing fields to display is a bit flakey
- Fixed [#1005]( https://github.com/SEED-platform/seed/issues/1005 ), Error in number of pages calculation
- Fixed [#1008]( https://github.com/SEED-platform/seed/issues/1008 ), catch invalid organization id
- Fixed [#1025]( https://github.com/SEED-platform/seed/issues/1025 ), Breakup Bluesky Model

Accepted External Pull Requests: 23
- Fixed [#977]( https://github.com/SEED-platform/seed/pull/977 ), fixes #976
- Fixed [#981]( https://github.com/SEED-platform/seed/pull/981 ), Fixes js error in getAggChartData
- Fixed [#983]( https://github.com/SEED-platform/seed/pull/983 ), Fix for #982 + modifications to Selenium test
- Fixed [#987]( https://github.com/SEED-platform/seed/pull/987 ), Tallus 982 better tests
- Fixed [#1002]( https://github.com/SEED-platform/seed/pull/1002 ), In superuser organization list (under Admin) show the Organization ID…
- Fixed [#1003]( https://github.com/SEED-platform/seed/pull/1003 ), 954 - Added selenium test to check year ending can be edited.
- Fixed [#1015]( https://github.com/SEED-platform/seed/pull/1015 ), Added Selenium Test Infrastructure
- Fixed [#1017]( https://github.com/SEED-platform/seed/pull/1017 ), Revert "Ftr/primarysecondary taxlots"
- Fixed [#1023]( https://github.com/SEED-platform/seed/pull/1023 ), 996 ui updates
- Fixed [#1034]( https://github.com/SEED-platform/seed/pull/1034 ), Fix for #1031 Investigate Sentry error
- Fixed [#1037]( https://github.com/SEED-platform/seed/pull/1037 ), Tallus selenium test 836
- Fixed [#1038]( https://github.com/SEED-platform/seed/pull/1038 ), Fix for #10131 cut against master
- Fixed [#1046]( https://github.com/SEED-platform/seed/pull/1046 ), Tallus tests consolidation
- Fixed [#1047]( https://github.com/SEED-platform/seed/pull/1047 ), Dmcq fresh detail after update
- Fixed [#1051]( https://github.com/SEED-platform/seed/pull/1051 ), Add search_properties and search_taxlots as equivalents to search_buildings
- Fixed [#1054]( https://github.com/SEED-platform/seed/pull/1054 ), Revert "Major UI Refactor"
- Fixed [#1055]( https://github.com/SEED-platform/seed/pull/1055 ), Tallus fix tests remove building views
- Fixed [#1056]( https://github.com/SEED-platform/seed/pull/1056 ), fix typos in test
- Fixed [#1058]( https://github.com/SEED-platform/seed/pull/1058 ), bug fix for buiding detail history views
- Fixed [#1059]( https://github.com/SEED-platform/seed/pull/1059 ), Add BE for Reports
- Fixed [#1060]( https://github.com/SEED-platform/seed/pull/1060 ), Tallus data cleansing
- Fixed [#1062]( https://github.com/SEED-platform/seed/pull/1062 ), Demo data with audit logs
- Fixed [#1064]( https://github.com/SEED-platform/seed/pull/1064 ), API backend for updating property/taxlot labels
- Fixed [#1066]( https://github.com/SEED-platform/seed/pull/1066 ), fix incorect url
