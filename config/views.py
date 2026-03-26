"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import mimetypes
import posixpath
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.utils._os import safe_join
from django.utils.http import http_date
from django.views.static import was_modified_since


def robots_txt(request, allow=False):
    env = getattr(settings, "ENV", "development").lower()

    if env == "production" or allow:
        content = "User-agent: *\nAllow: /"
    else:
        content = "User-agent: *\nDisallow: /"

    return HttpResponse(content, content_type="text/plain")


def _serve_file_bytes(request, fullpath):
    if fullpath.is_dir():
        raise Http404("Directory indexes are not allowed here.")
    if not fullpath.exists():
        raise Http404(f"{fullpath} does not exist")

    statobj = fullpath.stat()
    if not was_modified_since(request.META.get("HTTP_IF_MODIFIED_SINCE"), statobj.st_mtime):
        return HttpResponseNotModified()

    content_type, encoding = mimetypes.guess_type(str(fullpath))
    response = HttpResponse(fullpath.read_bytes(), content_type=content_type or "application/octet-stream")
    response.headers["Last-Modified"] = http_date(statobj.st_mtime)
    if encoding:
        response.headers["Content-Encoding"] = encoding
    return response


def debug_static_serve(request, path):
    normalized_path = posixpath.normpath(path).lstrip("/")
    absolute_path = finders.find(normalized_path)
    if not absolute_path:
        if path.endswith("/") or path == "":
            raise Http404("Directory indexes are not allowed here.")
        raise Http404(f"{path} could not be found")
    return _serve_file_bytes(request, Path(absolute_path))


def debug_media_serve(request, path):
    normalized_path = posixpath.normpath(path).lstrip("/")
    return _serve_file_bytes(request, Path(safe_join(settings.MEDIA_ROOT, normalized_path)))
