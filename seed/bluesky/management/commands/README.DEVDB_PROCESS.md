# Creating the development database

This document describes the process for creating a development
database that can be used for developing the migration from a users
perspective.

# Importing the new database

   psql# CREATE DATABASE seeddb WITH OWNER seeduser;
   $ psql seeddb < db/seed_prod-20160428.sql
   $ python manage.py migrate --fake-initial

# Deleting the old database

   psql# DROP DATABASE seeddb;

# The Core Users
   - Organization: CEC Diane(124): 6154, 959
   - Organization: City of Atlanta(181): 14540, 1010
   - Organization: City of Berkeley(117): 785, 177
   - Organization: City of Cambridge(69): 10257, 1002
   - Organization: City of Houston(6): 43494, 6648
   - Organization: City of Philadelphia(20): 33257, 2269
   - Organization: District of Columbia Department of Energy and Environment(7): 40232, 1624
   - Organization: Kansas City(156): 37844, 1436
   - Organization: Montgomery County DEP(10): 3546, 1163
   - Organization: New York City(49): 105662, 12988
   - Organization: Orange County Florida(105): 20630, 10296
   - Organization: Salt Lake City(126): 18141, 2258

## The Core User IDS
[124,181,117,69,6,20,7,156,10,49,105,126]

## Pre migrated
126,

156, 49, 69, 7
