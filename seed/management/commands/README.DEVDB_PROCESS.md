# Creating the development database

This document describes the process for creating a development
database that can be used for developing the migration from a users
perspective.

# Importing the new database

   psql# CREATE DATABASE seeddb WITH OWNER seeduser;
   $ psql seeddb < db/seed_prod-20160624.sql
   $ python manage.py migrate --fake-initial

# Deleting the old database

   psql# DROP DATABASE seeddb;

# The Core Users
   - Organization: City of Philadelphia(20): 33257, 2269
   - Organization: DC BlueSky Test(184)
   - Organization: New York City(49): 105662, 12988
   - Organization: City of Cambridge(69): 10257, 1002
   - Organization: Montgomery County DEP(10): 3546, 1163
   - Organization: City of Atlanta(181): 14540, 1010
   - Organization: Kansas City(156): 37844, 1436
   - Organization: City of Berkeley(117): 785, 177
   - Organization: CEC Diane(124): 6154, 959
   - Organization: Orange County Florida(105): 20630, 10296
   - Organization: Salt Lake City(126): 18141, 2258
   - Organization: City of Houston(6): 43494, 6648

## The Core User IDS

In prioritized order

[20, 184, 49, 69, 10, 184, 156, 117, 124, 105, 126, 6]
20,184,49,10,181,156,117,124,105,126,6
