# Release Instructions

#### Upgrading from 2.6.1-patch3
Within this patch, a new table field was created in the database to satisfy a time-sensitive enhancement needed for a 2.6.1 deployment. Separately, this enhancement was been incorporated into 2.7.0.

In any case where a deployment of SEED is on 2.6.1-patch3 (and has this new field in its database), upgrading to >= 2.7.0 would need to involve an extra step. Specifically, when running the migrations to update the database, the 0119_column_recognize_empty migration will need to be run separately and with the `--fake` flag.

```
./manage.py migrate seed 0119_column_recognize_empty --fake
```

Coming from 2.6.1-patch3, the database will already have the new recognize_empty field, so running 0119_column_recognize_empty _without the flag_ will cause an error when trying to create that field that already exists. Once this migration is run with the flag in isolation, the database state and Django's understanding of the database state will be aligned, and no further action is needed for this new field in order to keep the states in sync.
