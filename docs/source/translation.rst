Translating SEED
================

1. Update translations on `lokalise`_.

2. Copy lokalise.yml.example to lokalise.yml. Update API token.

3. Install lokalise locally

   .. code:: bash

      brew tap lokalise/cli-2
      brew install lokalise2

3. Run scripts if you have Lokalise CLI installed. If not, see scripts for manual steps.

   .. code:: bash

      script/get_python_translations.sh
      script/get_angular_translations.sh

4. Uncomment the ``useMissingTranslationHandlerLog`` line seed.js to log untranslated strings to the console for review

5. Verify and commit changes

**Note: The lokalize website is the canonical source of data. If you
change the locale files locally, then you need to push them to
lokalize.**

TL;DR

SEED is localized for more than just English, so a little more care is
needed as we add new UI. All translatable strings are held in either
per-language ``.json`` files (for Angular-controlled strings, which are
the majority), or ``.mo`` files (for strings supplied by Django).

At render time, SEED will sniff out the browser's ``Accept:`` header.
Based on that, we choose the right file. The language files themselves
are key->value mappings from a translation "key" to a translated value.
Either Angular or Django will then swap that value into the DOM wherever
it sees the key. If no translation is available, the key remains in the
DOM. (There are some wrinkles with HTML styling and pluralization that
we'll review below).

So, the basic flow on top of any new UI features is now:

1. Tag any user-visible strings in the UI as "translatable." There are
   currently 12 (!) ways in which to do this; see below.
2. Create the translation key at `lokalise`_. We're using lokalise
   because it can smooth over differences in the file formats that
   Angular and Django require, and is a nice tool for managing the
   process of getting translations done by a native speaker: we can put
   up screenshots to clarify how the translated phrase is used, track
   translation progress, etc.
3. Get a translation done. As a placeholder, lokalise can provide an
   auto-filled translation from Google Translate or a few other
   services, but it's fairly straightforward to order a professional
   translation through lokalise.
4. Pull new translation files into the right places in the source tree
   and commit them. There are scripts under ``/scripts`` to make this
   mostly automatic.
5. Visually check that the containing UI looks OK with the translated
   string(s). Some languages (e.g., French, German) can be wordy relative
   to English and cause UI elements like buttons to expand oddly. Adjust
   the layout or adjust the translation as needed.

.. _general-philosophies--style:

General philosophies / style
----------------------------

Don't go crazy with indirection and interpolation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's probably better to err on the side of too many keys than to get
clever with interpolation or Angular expressions to avoid
near-duplicates of keys. The aim should be that there is at least one
place where a competent translator can see the whole string at once.

Compare:

::

   <h2>{$:: inventory_type == 'taxlots' ?
         translations['INCLUDE_SHARED_TAXLOTS'] :
         translations['INCLUDE_SHARED']

.. _lokalise: https://lokalise.com/project/3537487659ca9b1dce98a7.36378626/?view=multi
