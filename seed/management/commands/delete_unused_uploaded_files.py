# -*- coding: utf-8 -*-
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from __future__ import unicode_literals

import os

from django.core.management.base import BaseCommand

from seed.data_importer.models import ImportFile


class Command(BaseCommand):
    help = 'Creates a default super user for the system tied to an organization'

    def add_arguments(self, parser):
        parser.add_argument('--org_id',
                            default=None,
                            help='Name of a specific organization to operate',
                            action='store',
                            dest='org_id')

    def handle(self, *args, **options):
        # In local dev and production the files are in the media/uploads folder.
        #
        # Steps to process
        #   1. The database has various paths of all the files as we have been
        #      moving the files around and the database paths have not been updated
        #      First task is to update the file paths to /seed/media/uploads for the files
        #   2. There is a deleted column in SEED that is updated when a user removes the
        #      file from the frontend; however, SEED persists the file. This tasks
        #      deletes the files from disk (if they exist), but it does not delete the
        #      ImportFile record itself

        org_id = options['org_id']
        if org_id:
            files = ImportFile.objects.get_all().filter(import_record__super_organization=org_id)  # this actually returns a queryset
        else:
            files = ImportFile.objects.get_all()

        # fix the file path if it is not /seed/media/uploads
        # populate the list of files - this may need to be broken up into multiple tasks on the real data
        # based on how large the directory / table is.
        rename_files = []
        for f in files:
            filename = f.file.name
            if os.path.exists(filename):
                # don't do anything if the path exists
                continue

            # the filename/path is not correct and needs to be updated
            # put it in a tuple of db object, oldname, new name
            new_base_path = "/seed/media/uploads"
            if filename.startswith(new_base_path):
                # don't do anything, file name is in the right format for
                # docker mounted media
                continue
            elif filename == "":
                # no file attached
                continue
            else:
                if 'pm_imports/' in filename:
                    # this is a special folder that needs to persist in the uploads directory
                    rename_files.append((f, filename, f"{new_base_path}/pm_imports/{os.path.basename(filename)}"))
                else:
                    rename_files.append((f, filename, f"{new_base_path}/{os.path.basename(filename)}"))

        self.stdout.write('********    LIST OF IMPORT FILE PATHS TO RENAME  *********')
        for f in rename_files:
            print(f"Will rename {f[1]} to {f[2]}")
        self.stdout.write('********    END OF LIST (list may be blank)    *********')
        f = input("Are you sure you want to rename all of the files above? Use with caution! [Y/y]? ")
        if f.lower() == 'y':
            for f in rename_files:
                f_db = f[0]
                print(f"Renaming {f[1]} to {f[2]}")
                f_db.file.name = f[2]
                f_db.save()
            self.stdout.write('Done renaming', ending='\n')
        else:
            self.stdout.write('Not renaming, will not continue, exiting')
            exit()

        # now go through and find the deleted=True and remove the records
        if org_id:
            files = ImportFile.objects.get_all().filter(deleted=True, import_record__super_organization=org_id).exclude(file__exact='')
        else:
            files = ImportFile.objects.get_all().filter(deleted=True).exclude(file__exact='')

        f = input(f"Are you sure you want to delete {len(files)} InputFiles that have been marked with 'deleted'? Use with caution! [Y/y]? ")
        if f.lower() == 'y':
            for fil in files:
                filename = fil.file.name
                self.stdout.write(f"Deleting file {filename}")
                # regardless if the file exists or not,
                fil.file.delete(save=True)

            self.stdout.write('Done deleting flagged record files, the records still exist', ending='\n')
        else:
            self.stdout.write('Not deleting, exiting')
            exit()
