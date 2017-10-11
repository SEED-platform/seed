# Translating SEED

The flow:

1. Tag the UI
2. Automatically extract tags
3. Upload to lokalise.co
4. Translate
5. Pull new translation files into source tree

## Philosophy

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


## 1. Tag the UI
## 2. Automatically extract tags
## 3. Upload to lokalise.co
## 4. Translate
## 5. Pull new translation files into source tree

There are two scripts for this: `script/get_python_translations` and
`script/get_angular_translations`.

You'll need `msgfmt` (from GNU gettext) on `$PATH` to run the python getter, as
we need to re-compile the `.po` file for Django. Note that Mac homebrew does
not put this on path by default.
