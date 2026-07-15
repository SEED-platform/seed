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


def seed_angular(request):
    requested_path = request.path.replace("/ng-app/", "", 1)

    # Serve static files first
    if requested_path and "." in requested_path:
        static_path = Path(settings.STATIC_ROOT) / "ng-app" / requested_path
        if static_path.exists():
            return _serve_file(request, static_path)

    # Otherwise serve index.html
    index_path = Path(settings.STATIC_ROOT) / "ng-app" / "index.html"
    if not index_path.exists():
        raise Http404("seed-angular static files not found")
    return _serve_file(request, index_path, content_type="text/html", streaming=False)
