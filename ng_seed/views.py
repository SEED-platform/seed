import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse


def _serve_file(path, content_type=None):
    if content_type is None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return HttpResponse(path.read_bytes(), content_type=content_type)


def seed_angular(request):
    requested_path = request.path.replace("/ng-app/", "", 1)

    # Serve static files first
    if requested_path and "." in requested_path:
        static_path = Path(settings.STATIC_ROOT) / "ng-app" / requested_path
        if static_path.exists():
            return _serve_file(static_path)

    # Otherwise serve index.html
    index_path = Path(settings.STATIC_ROOT) / "ng-app" / "index.html"
    if not index_path.exists():
        raise Http404("seed-angular static files not found")
    return _serve_file(index_path, content_type="text/html")
