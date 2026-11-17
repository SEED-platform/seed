import { HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { Router } from '@angular/router'
import { firstValueFrom, of, throwError } from 'rxjs'
import { ErrorService } from '@seed/services'
import { authInterceptor } from 'app/core/auth/auth.interceptor'
import { AuthService } from 'app/core/auth/auth.service'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { MediaService } from './media.service'

describe('MediaService', () => {
  let service: MediaService
  let http: HttpTestingController
  let errorService: jasmine.SpyObj<ErrorService>
  let snackBar: jasmine.SpyObj<SnackBarService>

  beforeEach(() => {
    errorService = jasmine.createSpyObj<ErrorService>('ErrorService', ['handleError'])
    errorService.handleError.and.callFake((_error: HttpErrorResponse, message: string) => throwError(() => new Error(message)))
    snackBar = jasmine.createSpyObj<SnackBarService>('SnackBarService', ['alert'])

    TestBed.configureTestingModule({
      providers: [
        // Use the app's auth interceptor to check that media requests get the user's token
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { accessToken: 'test-token', isAuthenticated: () => of(true) } },
        { provide: Router, useValue: {} },
        { provide: ErrorService, useValue: errorService },
        { provide: SnackBarService, useValue: snackBar },
      ],
    })
    service = TestBed.inject(MediaService)
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
  })

  describe('toApiUrl', () => {
    it('keeps media endpoint URLs', () => {
      expect(service.toApiUrl('/api/v3/media/inventory_documents/report%20v2.pdf')).toBe(
        '/api/v3/media/inventory_documents/report%20v2.pdf',
      )
    })

    it('maps development media URLs to the media endpoint', () => {
      expect(service.toApiUrl('/media/analysis_output_files/building%20report.html')).toBe(
        '/api/v3/media/analysis_output_files/building%20report.html',
      )
      expect(service.toApiUrl('/media/buildingsync_files/building.xml')).toBe('/api/v3/media/buildingsync_files/building.xml')
    })

    it('maps same-origin absolute URLs and rejects other origins', () => {
      expect(service.toApiUrl(`${window.location.origin}/media/inventory_documents/photo.png`)).toBe(
        '/api/v3/media/inventory_documents/photo.png',
      )
      expect(service.toApiUrl('https://example.com/api/v3/media/uploads/data.csv')).toBeNull()
    })

    it('maps absolute server paths by their path under the media directory, encoding each segment', () => {
      expect(service.toApiUrl('/seed/media/uploads/pm_imports/my data #1.csv')).toBe(
        '/api/v3/media/uploads/pm_imports/my%20data%20%231.csv',
      )
      expect(service.toApiUrl('C:\\NREL\\seed\\media\\uploads\\data.xlsx')).toBe('/api/v3/media/uploads/data.xlsx')
      // the first `media` directory isn't MEDIA_ROOT, since a served directory doesn't follow it
      expect(service.toApiUrl('/media/disk/seed/media/uploads/data.csv')).toBe('/api/v3/media/uploads/data.csv')
    })

    it('rejects references that are not media files', () => {
      expect(service.toApiUrl(null)).toBeNull()
      expect(service.toApiUrl(undefined)).toBeNull()
      expect(service.toApiUrl('')).toBeNull()
      expect(service.toApiUrl('/seed/uploads/data.csv')).toBeNull()
      expect(service.toApiUrl('/seed/media/uploads')).toBeNull()
      expect(service.toApiUrl('/seed/media/simulation_files/model.osm')).toBeNull()
    })

    it('rejects references that resolve outside the media endpoint', () => {
      expect(service.toApiUrl('/api/v3/media/../users/')).toBeNull()
      expect(service.toApiUrl('/media/uploads/%2e%2e/%2e%2e/users/')).toBeNull()
      expect(service.toApiUrl('/seed/media/uploads/../../users/')).toBeNull()
    })
  })

  it('fetches files from the media endpoint through HttpClient with the access token', () => {
    let result: Blob | undefined
    service.getBlob('/seed/media/uploads/data.csv').subscribe((blob) => (result = blob))

    const request = http.expectOne('/api/v3/media/uploads/data.csv')
    expect(request.request.method).toBe('GET')
    expect(request.request.responseType).toBe('blob')
    expect(request.request.headers.get('Authorization')).toBe('Bearer test-token')

    const blob = new Blob(['a,b'])
    request.flush(blob)
    expect(result).toBe(blob)
  })

  it('reports failed requests with the error service', () => {
    let error: Error | undefined
    service.getBlob('/media/uploads/data.csv').subscribe({ error: (e: Error) => (error = e) })

    http.expectOne('/api/v3/media/uploads/data.csv').flush(new Blob(), { status: 404, statusText: 'Not Found' })

    expect(errorService.handleError).toHaveBeenCalledWith(jasmine.any(HttpErrorResponse), 'Error fetching file')
    expect(error?.message).toBe('Error fetching file')
  })

  it('reports files that are not available without making a request', () => {
    let error: Error | undefined
    service.download(null).subscribe({ error: (e: Error) => (error = e) })

    http.expectNone(() => true)
    expect(snackBar.alert).toHaveBeenCalledWith('File is not available')
    expect(error).toBeDefined()
  })

  it('fetches text', async () => {
    const text = firstValueFrom(service.getText('/media/analysis_output_files/report.html'))

    http.expectOne('/api/v3/media/analysis_output_files/report.html').flush(new Blob(['<p>Report</p>'], { type: 'text/html' }))

    expect(await text).toBe('<p>Report</p>')
  })

  it('fetches data: URLs', async () => {
    const dataUrl = firstValueFrom(service.getDataUrl('/media/analysis_output_files/plot.png'))

    http.expectOne('/api/v3/media/analysis_output_files/plot.png').flush(new Blob(['png'], { type: 'image/png' }))

    expect(await dataUrl).toBe(`data:image/png;base64,${btoa('png')}`)
  })

  describe('download', () => {
    let anchor: HTMLAnchorElement
    let createObjectURL: jasmine.Spy<(blob: Blob) => string>

    beforeEach(() => {
      anchor = document.createElement('a')
      spyOn(anchor, 'click')
      spyOn(document, 'createElement').and.returnValue(anchor)
      createObjectURL = spyOn(URL, 'createObjectURL').and.returnValue('blob:test')
      spyOn(URL, 'revokeObjectURL')
    })

    it('saves the file as an octet stream so it cannot render', () => {
      service.download('/media/inventory_documents/page.html', 'page.html').subscribe()

      http.expectOne('/api/v3/media/inventory_documents/page.html').flush(new Blob(['<script></script>'], { type: 'text/html' }))

      const [blob] = createObjectURL.calls.mostRecent().args
      expect(blob.type).toBe('application/octet-stream')
      expect(anchor.href).toBe('blob:test')
      expect(anchor.download).toBe('page.html')
      expect(anchor.click).toHaveBeenCalled()
    })

    it('names the file after the media file, keeping its extension, by default', () => {
      service.download('/api/v3/media/analysis_output_files/building%20report.html').subscribe()

      http.expectOne('/api/v3/media/analysis_output_files/building%20report.html').flush(new Blob(['report']))

      expect(anchor.download).toBe('building report.html')
    })
  })
})
