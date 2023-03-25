#!/usr/bin/env bash

# If Lokalise CLI isn't installed, download fr_CA.po and en_US.po files with
# the settings listed below (including comments, sorting from A-Z, and replacing
# empty translations with the base language).

# Then, as shown in the code below, rename the unzipped .po files to django.po
# and move them into the corresponding directories:
# - locale/fr_CA/LC_MESSAGES/
# - locale/en_US/LC_MESSAGES/

# Then, assuming msgfmt is installed, run the `msgfmt` command
# with the -o option referencing each of these django.po files.

if [[ ! -f lokalise.yml ]]; then
  echo "Missing lokalise.yml. Copy from lokalise.yml.example"
  exit 1
fi

tmp=tmp/python_locales
dest=locale

mkdir -p $tmp

lokalise2                    \
  --config=lokalise.yml      \
    file download            \
  --filter-langs=fr_CA,en_US \
  --format=po              \
  --include-comments=true    \
  --export-sort=a_z          \
  --export-empty-as=base     \
  --unzip-to=$tmp            \
  --original-filenames=false

mv $tmp/locale/fr_CA.po $dest/fr_CA/LC_MESSAGES/django.po
msgfmt -o $dest/fr_CA/LC_MESSAGES/django.{mo,po}

mv $tmp/locale/en_US.po $dest/en_US/LC_MESSAGES/django.po
msgfmt -o $dest/en_US/LC_MESSAGES/django.{mo,po}

rm -rf $tmp
