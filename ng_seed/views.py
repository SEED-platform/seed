import os

from django.conf import settings
from django.http import FileResponse, Http404


def seed_angular(request):
    requested_path = request.path.replace("/ng-app/", "", 1)

    # Serve static files first
    if requested_path and "." in requested_path:
        static_path = os.path.join(settings.STATIC_ROOT, "ng-app", requested_path)
        if os.path.exists(static_path):
            return FileResponse(open(static_path, "rb"), content_type=None)

    # Otherwise serve index.html
    index_path = os.path.join(settings.STATIC_ROOT, "ng-app", "index.html")
    if not os.path.exists(index_path):
        raise Http404("seed-angular static files not found")
    return FileResponse(open(index_path, "rb"), content_type="text/html")
