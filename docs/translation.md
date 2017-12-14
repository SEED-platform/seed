# Translating SEED

SEED is localized for more than just English, so a little more care is needed
as we add new UI. All translatable strings are held in either per-language `.json` files
(for Angular-controlled strings, which are the majority), or `.mo` files (for
strings supplied by Django).

At render time, SEED will sniff out the browser's `Accept:` header. Based on
that, we choose the right file. The language files themselves are key->value
mappings from a translation "key" to a translated value. Either Angular or
Django will then swap that value into the DOM wherever it sees the key. If no
translation is available, the key remains in the DOM.  (There are some wrinkles
with HTML styling and pluralization that we'll review below).

So, the basic flow on top of any new UI features is now:

1. Tag any user-visible strings in the UI as "translatable." There are
   currently 12 (!) ways in which to do this; see below.
2. Create the translation key at
   [lokalise](https://lokalise.co/project/3537487659ca9b1dce98a7.36378626/?view=multi).
   We're using lokalise because it can smooth over differences in the file
   formats that Angular and Django require, and is a nice tool for managing the
   process of getting translations done by a native speaker: we can put up
   screenshots to clarify how the translated phrase is used, track translation
   progress, etc.
4. Get a translation done. As a placeholder, lokalise can provide an
   auto-filled translation from Google Translate or a few other services, but
   it's fairly straightforward to order a professional translation through
   lokalise.
5. Pull new translation files into the right places in the source tree and
   commit them. There are scripts under `/scripts` to make this mostly
   automatic.
6. Visually check that the containing UI looks OK with the translated
   string(s). Some languages (eg. French, German) can be wordy relative to
   English and cause UI elements like buttons to expand oddly. Adjust the
   layout or adjust the translation as needed.

## General philosophies / style

### Don't go crazy with indirection and interpolation

It's probably better to err on the side of too many keys than to get clever
with interpolation or Angular expressions to avoid near-duplicates of keys. The
aim should be that there is at least one place where a competent translator can
see the whole string at once.

Compare:

```
<h2>{$:: inventory_type == 'taxlots' ?
      translations['INCLUDE_SHARED_TAXLOTS'] :
      translations['INCLUDE_SHARED_PROPERTIES'] $}</h2>
```

to

```
<h3 translate="SOME_KEY"
    translate-values="{ interpolated_value: some_transform_in_scope(a_variable) }"></h3>
```

with a translation string of

```
{ "SOME_KEY": "This is a phrase to {$ interpolated_value $}" }
```

The interpolated value is context that is invisible to the translator, who
generally won't be seeing the code. Some interpolation (eg. plurals) is
necessary. Near dupes are somewhat annoying but also fundamentally low-cost
and simple. Messy, spread-out contexts actively impede understanding.

### English as keys

A missing translation will simply show the "key."

Short labels and bits of text (eg. username) should just use the English word
"Username" as the tag, and if the translation is missing the key will be shown
and the UI will effectively be in English. This isn't a great experience for
foreign-language speakers, but it probably won't actively impede their work.
The meaning is there and available.

Longer chunks of explanatory text, though, should use a short key eg.
`MARKETING_BULLETS.BULLET_ONE` and provide the full text in the translation
file. The reason for this is that the key is the way we look up the
translation. Longer copy could have minor tweaks to it, and this will make the
system unable to look up the translation, and we'll have to reconnect the
translation in every file. Better here to use an abstract key. The downside
is that the copy is no longer available in-line in the HTML.

There's not really a hard dividing line here.

### Reducing duplicate keys

Try not to pull in punctuation. Try to scope the translation key to eg.
"Username", not "Username:". This helps us get more key "hits" and minimizes
dupes in the translation file.

### Unicode 👍, HTML entities `&thumbsdown;`

It seems best to just put UTF-8 directly into the translated value where
possible and steer clear of angular-translate's sanitization machinery:
minimize the opportunities for double-encoding bugs.

There are two scripts for this: `script/get_python_translations` and
`script/get_angular_translations`.

You'll need `msgfmt` (from GNU gettext) on `$PATH` to run the python getter, as
we need to re-compile the `.po` file for Django. Note that Mac homebrew does
not put this on path by default.

## Regarding XSS

**There is (currently) a specific problem with XSS that will be addressed by the
time this PR merges. This temporary section is for explanation.**

There are about 20 keys that currently contain HTML tags for styling (eg.
`<strong>`, or inline icons). These should simply be included in the
translation string on the principle that otherwise we have chopped up,
decontextualized translation strings that are hard for the translators to
manage.

Our particular problem is when we need to interpolate into a styled string.

(see the angular translate [security guide][translate-security]).

- If we use the escape sanitization strategy, we lose our styling.
- If we use the sanitize strategy, we keep our styling, successfully strip out any `<script>` tags, but also double escapes any UTF-8 accented characters (see this 2015 [bug](https://github.com/angular-translate/angular-translate/issues/1101).
- If we use the sce strategy, we keep our styles, keep our accents, but don't get any XSS protection (eg. a `<script>` tag in a translation string or, worse, say a cycle name, get executed).

Options:

1. make up some DSL to use in the strings for the HTML tags we do use, like `*
   bold *` or `icon.check-quare-o`. Implement a filter to re-inject these where
   they happen but after translation.

2. Better understand the `sceParameters` or `escapeParameters` options.

(DISCUSS: Nick ... might have just solved this in my head. Will try out and advise).

## Tagging Strings

### Tagging in Angular

#### Form 1

`<h1 translate>SOME KEY</h1>`

In Angular HTML. Bread-and-butter, understandable. This is ideally most of the
translated UI strings. The more we can use this form, the more amenable the
project is to automatic extraction of translateable strings for upload to
lokalise.

#### Form 2
`<h1 translate="SOME_KEY" translate-values="{ count: $scope.thing.length }"></h1>`

In Angular HTML. This form is for when we need to interpolate into the translated
string. This can happen either:

- to prevent having to chop up the keys to accommodate some variable content,
  eg. `Your file contains '{count}' properties`, or

- to accommodate pluralization without having to provide a key for each count.
  Interpolation uses `messageformat` and this supercedes `ng-pluralize`. The
  form of the translated value in lokalize could then be eg. `You have
  {num_properties, plural, one{one property} other {many properties}}` Refer to the 
  [messageformat docs][messageformat].

#### Form 3
`<h1>{$ 'SOME_KEY' | translate $}</h1>`

In Angular HTML. Functionally equivalent to Form 1. This form might be
necessary if there are scope conflict issues that prevent the tag property
version from working, or font-awesome icons are contained within the enclosing
tag, or you want to exclude punctuation from the key.

#### Form 4

`<translate>Cancel</translate>`

In Angular HTML. Functionally equivalent to `{$:: 'Cancel' | translate $}`.
Also useful when you don't already have a `<span>` or similar to apply the
translation directive to.

#### Form 5

`$translate.instant('SOME_KEY')`

`$translate.instant('SOME_KEY', interpolationParams)`

In Angular JS. For spot translations that need to be stuffed into data
structures for whatever reason.

#### Form 6
```
$translate(keys).then(function success (objectWithTranslationKeys->Values) {
    // stash in a var, or on $scope
  }, function failed (objectWithTranslationKeys->Keys) {
    // report failure?
  });`
```

In Angular JS, particularly controllers. Here you can bulk-translate an array
of keys, and attach it to `$scope` for later use in template expressions as
`translations[SOME_KEY]`, or later in the controller.  Note that it's async, so
if needed smooth over render timing problems with Form 5.

Form 6 also lets you clean up translations in the templates with forms like
`<h1>{$:: if predicate ? translate['KEY1'] : translate['KEY2'] $}</h1>`, which
seems to happen a lot around the similar UI for properties versus tax lots.

#### Form 7

`i18nService.setCurrentLang(stripRegion($translate.use()));`

In JS controller code that involves ui-grid. The ui-grid plugin has its own
localization system and language files. This snippet feeds what
angular-translate understands the current language to be into ui-grid, so that
the menus get translated (eg. "Export as CSV").

(Note that ui-grid only has a `fr` localization, and doesn't understand that
`fr_CA` should fall back to `fr`. Hence the stripping of the region).

#### Form 8

`columnDefs: [{ ... headerCellFilter: 'translate', cellFilter: 'translate, ...}]`

This translates the dynamic data supplied to ui-grid, using angular-translate's filter.

#### Form 9

`$sce.getTrustedHtml($translate.instant(key, params));`

Translates an interpolated key in a notification, or some other context where
render timing doesn't allow the promise-based translation, and unwraps it since
it doesn't seem the notification plugin plays well with SCE. Refer to XSS
section above.

### Tagging in Django

There is very little translation happening in Django, and it appears to be less
fragmented overall than Angular. There are only three forms. See also the
excellent [Django
documentation](https://docs.djangoproject.com/en/1.11/topics/i18n/translation/).

#### Form 1

`{% trans 'SOME KEY' %}`

For short translations in Django-managed templates.

#### Form 2

`{% blocktrans trimmed %}SOME KEY{% endblocktrans %}`

For longer translations in Django-managed templates. See above in philosophies re: using the
actual translation text as a key.

#### Form 3

`_('SOME_KEY')`

For translations within Python code. There are some [subtleties around
laziness](https://docs.djangoproject.com/en/1.11/topics/i18n/translation/#working-with-lazy-translation-objects)
but generally this hasn't been an issue in the small number of strings under
Django's control.

## References 

- [angular-translate docs][angular-translate]
- lokalize [command line tool][lokalize-cli]
- [messageformat.js][messageformat]

[angular-translate]: https://angular-translate.github.io/docs/#/guide
[messageformat]: https://messageformat.github.io
[lokalise-cli]: https://docs.lokalise.co/article/44l4f1hiZM-lokalise-cli-tool
[translate-security]: https://angular-translate.github.io/docs/#/guide/19_security
