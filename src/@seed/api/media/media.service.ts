import type { HttpErrorResponse } from '@angular/common/http'
import { HttpClient } from '@angular/common/http'
import { inject, Injectable } from '@angular/core'
import type { Observable } from 'rxjs'
import { catchError, from, map, switchMap, throwError } from 'rxjs'
import { ErrorService } from '@seed/services'
import { blobToDataUrl, downloadBlob } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

// The backend's authenticated media endpoint (the default MEDIA_URL)
const MEDIA_API_PATH = '/api/v3/media/'
// MEDIA_URL in the backend's development settings, served by the same authenticated view
const DEV_MEDIA_PATH = '/media/'
// Directories under MEDIA_ROOT that the media endpoint serves
const MEDIA_BASE_DIRS = new Set(['analysis_input_files', 'analysis_output_files', 'buildingsync_files', 'inventory_documents', 'uploads'])

/**
 * Fetches media files (imports, inventory documents, analysis outputs, ...) through HttpClient so the auth interceptor
 * attaches the user's token. Links, iframes, and images can't send it, and the app signs in with JWTs only
 */
@Injectable({ providedIn: 'root' })
export class MediaService {
  private _errorService = inject(ErrorService)
  private _httpClient = inject(HttpClient)
  private _snackBar = inject(SnackBarService)

  /**
   * Returns the media endpoint URL for a file reference from the API, or null if it isn't a media file. A reference can
   * be a media URL (`/api/v3/media/...`, or `/media/...` in development), a same-origin absolute URL, or an absolute
   * path on the server (e.g., an import file's `file`)
   */
  toApiUrl(fileOrUrl: string | null | undefined): string | null {
    const path = this._toSameOriginPath(fileOrUrl)
    if (!path) return null

    const url = this._toMediaApiPath(path)
    // Reject anything that resolves outside the media endpoint (e.g., with `..` segments)
    return url && this._resolvesToMediaApi(url) ? url : null
  }

  /**
   * Fetches a media file as a blob
   */
  getBlob(fileOrUrl: string | null | undefined): Observable<Blob> {
    return this._getBlob(fileOrUrl, 'Error fetching file')
  }

  /**
   * Fetches a media file as text (e.g., an HTML report)
   */
  getText(fileOrUrl: string | null | undefined): Observable<string> {
    // Decode the blob instead of requesting text, so a failed request reports the default error rather than its body
    return this.getBlob(fileOrUrl).pipe(switchMap((blob) => from(blob.text())))
  }

  /**
   * Fetches a media file as a data: URL (e.g., for an image, since the CSP allows data: but not blob: images)
   */
  getDataUrl(fileOrUrl: string | null | undefined): Observable<string> {
    return this.getBlob(fileOrUrl).pipe(switchMap((blob) => blobToDataUrl(blob)))
  }

  /**
   * Downloads a media file, named `filename` or else the file's name
   */
  download(fileOrUrl: string | null | undefined, filename?: string): Observable<void> {
    return this._getBlob(fileOrUrl, 'Error downloading file').pipe(
      map((blob) => {
        // Files can be uploaded by any member, so never give an HTML or SVG file a type that the browser would render
        const file = new Blob([blob], { type: 'application/octet-stream' })
        downloadBlob(file, filename || this._filename(this.toApiUrl(fileOrUrl)))
      }),
    )
  }

  private _getBlob(fileOrUrl: string | null | undefined, errorMessage: string): Observable<Blob> {
    const url = this.toApiUrl(fileOrUrl)
    if (!url) {
      this._snackBar.alert('File is not available')
      return throwError(() => new Error(`File is not available: ${fileOrUrl}`))
    }

    return this._httpClient.get(url, { responseType: 'blob' }).pipe(
      catchError((error: HttpErrorResponse) => {
        return this._errorService.handleError(error, errorMessage)
      }),
    )
  }

  // Reduces a same-origin absolute URL (e.g., from a serializer given the request) to its path. Other origins aren't
  // media files, and the auth interceptor only sends the token with relative API URLs
  private _toSameOriginPath(fileOrUrl: string | null | undefined): string | null {
    if (!fileOrUrl) return null
    if (!/^https?:\/\//i.test(fileOrUrl)) return fileOrUrl

    try {
      const url = new URL(fileOrUrl)
      return url.origin === window.location.origin ? url.pathname : null
    } catch {
      return null
    }
  }

  private _toMediaApiPath(path: string): string | null {
    if (path.startsWith(MEDIA_API_PATH)) return path
    if (this._isDevMediaUrl(path)) return `${MEDIA_API_PATH}${path.slice(DEV_MEDIA_PATH.length)}`
    return this._filePathToApiPath(path)
  }

  // A path on the server can also start with `/media/` (e.g., `/media/disk/seed/media/uploads/...`), so only treat it as
  // an (already encoded) URL when a served directory follows
  private _isDevMediaUrl(path: string): boolean {
    const [baseDir] = path.slice(DEV_MEDIA_PATH.length).split('/')
    return path.startsWith(DEV_MEDIA_PATH) && MEDIA_BASE_DIRS.has(baseDir)
  }

  // Maps an absolute path on the server, like `/seed/media/uploads/file.csv` or `C:\seed\media\uploads\file.csv`, to the
  // media endpoint by its path relative to MEDIA_ROOT (the `media` directory followed by a directory that it serves)
  private _filePathToApiPath(path: string): string | null {
    const segments = path.split(/[\\/]/).filter(Boolean)
    const mediaIndex = segments.findIndex((segment, i) => segment === 'media' && MEDIA_BASE_DIRS.has(segments[i + 1]))
    if (mediaIndex === -1) return null

    const relativeSegments = segments.slice(mediaIndex + 1)
    // Expect at least a base directory and a file name
    if (relativeSegments.length < 2) return null
    return `${MEDIA_API_PATH}${relativeSegments.map((segment) => encodeURIComponent(segment)).join('/')}`
  }

  private _resolvesToMediaApi(url: string): boolean {
    const { origin, pathname } = new URL(url, window.location.origin)
    return origin === window.location.origin && pathname.startsWith(MEDIA_API_PATH) && pathname.length > MEDIA_API_PATH.length
  }

  private _filename(url: string | null): string {
    const name = url?.split('/').pop() ?? ''
    try {
      return decodeURIComponent(name)
    } catch {
      return name
    }
  }
}
