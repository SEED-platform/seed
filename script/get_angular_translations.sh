#!/usr/bin/env bash

# If Lokalise CLI isn't installed, download the translation json files with
# the settings listed below (including comments, sorting from A-Z, and replacing
# empty translations with the base language).

# Then, as shown in the code below, move the unzipped .json files into the
# seed/static/seed/locales directory.

if [[ ! -f lokalise.yml ]]; then
  echo "Missing lokalise.yml. Copy from lokalise.yml.example"
  exit 1
fi

tmp=tmp/angular_locales
dest=seed/static/seed/locales

mkdir -p $tmp

lokalise2                       \
  --config=lokalise.yml         \
    file download               \
  --filter-langs=en_US,es,fr_CA \
  --format=json                 \
  --include-comments=true       \
  --export-sort=a_z             \
  --export-empty-as=base        \
  --unzip-to=$tmp               \
  --original-filenames=false

mv $tmp/locale/en_US.json $dest
mv $tmp/locale/es.json $dest
mv $tmp/locale/fr_CA.json $dest
rm -rf $tmp
