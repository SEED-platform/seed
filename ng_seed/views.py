"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import mimetypes
from pathlib import Path

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


class AsyncFileResponse(FileResponse):
    async def __aiter__(self):
        if self.file_to_stream is None:
            async for chunk in super().__aiter__():
                yield chunk
            return

        while True:
            chunk = await sync_to_async(self.file_to_stream.read, thread_sensitive=True)(self.block_size)
            if not chunk:
                break
            yield self.make_bytes(chunk)


def _serve_file(request, path, content_type=None, streaming=True):
    guessed_content_type, encoding = mimetypes.guess_type(path.name)
    content_type = content_type or guessed_content_type or "application/octet-stream"

    if not streaming:
        response = HttpResponse(path.read_bytes(), content_type=content_type)
    else:
        response = AsyncFileResponse(path.open("rb"), content_type=content_type)

    if encoding:
        response.headers["Content-Encoding"] = encoding
    return response


def _contained_file(root, requested_path):
    """Return the regular file at root/requested_path, or None if it is missing, not a regular file, or resolves outside root.

    Symlinks are followed before the containment check, so a link inside root that points outside it is not served.
    """
    # An absolute requested_path (including Windows drive and UNC paths) would replace root, so reject it before touching the filesystem
    if Path(requested_path).anchor:
        return None
    root = root.resolve()
    try:
        # resolve() collapses ".." and follows symlinks, so check containment on the result
        candidate = (root / requested_path).resolve()
    except (OSError, ValueError):  # e.g. an embedded NUL byte on POSIX
        return None
    if candidate.is_relative_to(root) and candidate.is_file():
        return candidate
    return None


def seed_angular(request):
    requested_path = request.path_info.replace("/ng-app/", "", 1)
    ng_app_root = Path(settings.STATIC_ROOT) / "ng-app"
    browser_root = ng_app_root / "browser"

    # Serve static files first
    if requested_path and "." in requested_path:
        for root in (ng_app_root, browser_root):
            static_path = _contained_file(root, requested_path)
            if static_path is not None:
                return _serve_file(request, static_path)

    # Otherwise serve index.html
    index_path = ng_app_root / "index.html"
    if not index_path.exists():
        index_path = browser_root / "index.html"
    if not index_path.exists():
        raise Http404("seed-angular static files not found")
    return _serve_file(request, index_path, content_type="text/html", streaming=False)
