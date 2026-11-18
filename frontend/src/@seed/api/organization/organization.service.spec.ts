import type { HttpEvent } from '@angular/common/http'
import { HttpEventType, provideHttpClient } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { NEVER } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { InventoryService } from '../inventory'
import { UserService } from '../user'
import { OrganizationService } from './organization.service'
import type { UploadAccessLevelInstancesResponse } from './organization.types'

describe('OrganizationService uploads', () => {
  let service: OrganizationService
  let http: HttpTestingController

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: UserService, useValue: { currentOrganizationId$: NEVER } },
        { provide: InventoryService, useValue: {} },
        { provide: ErrorService, useValue: {} },
        { provide: SnackBarService, useValue: {} },
      ],
    })
    service = TestBed.inject(OrganizationService)
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
  })

  it('requests upload progress and forwards progress events and the upload response', () => {
    const file = new File(['name\nBuilding'], 'instances.csv', { type: 'text/csv' })
    const events: HttpEvent<UploadAccessLevelInstancesResponse>[] = []
    service.uploadAccessLevelInstances(7, file).subscribe((event) => events.push(event))

    const request = http.expectOne('/api/v3/organizations/7/access_levels/importer/')
    expect(request.request.method).toBe('PUT')
    expect(request.request.reportUploadProgress).toBeTrue()
    expect(request.request.reportDownloadProgress).toBeFalse()

    const body: unknown = request.request.body
    expect(body).toBeInstanceOf(FormData)
    if (!(body instanceof FormData)) {
      throw new Error('Expected an upload form')
    }
    expect(body.get('file')).toEqual(file)

    const progress = { type: HttpEventType.UploadProgress, loaded: 50, total: 100 } as const
    request.event(progress)
    expect(events).toContain(progress)

    const response: UploadAccessLevelInstancesResponse = { success: true, tempfile: 'instances.csv' }
    request.flush(response)
    const lastEvent = events.at(-1)
    expect(lastEvent?.type).toBe(HttpEventType.Response)
    if (lastEvent?.type === HttpEventType.Response) {
      expect(lastEvent.body).toEqual(response)
    }
  })
})
