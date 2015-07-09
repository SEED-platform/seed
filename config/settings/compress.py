"""
:copyright: (c) 2014 Building Energy Inc
"""
"""
    Used with django-compress to properly link relative links (i.e. image urls)
    within less files while compiling them to css files.
    `DEBUG` should be `True` to get compress to have the indented behavior.
    See bin/post_compile for current use.
    Example:
        ./manage compress --force --settings=config.settings.compress
"""
try:
    from config.settings.local_untracked import *  # noqa
except ImportError:
    pass
DEBUG = True
