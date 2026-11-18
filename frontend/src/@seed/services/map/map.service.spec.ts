import { provideHttpClient } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { MapService } from './map.service'

describe('MapService', () => {
  let service: MapService
  let http: HttpTestingController

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
    service = TestBed.inject(MapService)
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
  })

  it('should cache string tract IDs before notifying the caller that status is ready', () => {
    const statusReady = jasmine.createSpy('statusReady').and.callFake(() => {
      expect(service.isDisadvantaged('01001020100')).toBeTrue()
      expect(service.isDisadvantaged('01001020200')).toBeFalse()
    })
    service.checkDisadvantagedStatus(['01001020100', '01001020200']).subscribe(statusReady)

    const request = http.expectOne('/api/v3/eeej/filter_disadvantaged_tracts/')
    expect(request.request.method).toBe('POST')
    expect(request.request.body).toEqual({ tract_ids: ['01001020100', '01001020200'] })
    expect(statusReady).not.toHaveBeenCalled()

    request.flush({ status: 'success', disadvantaged: ['01001020100'] })

    expect(statusReady).toHaveBeenCalledTimes(1)
  })

  it('should immediately notify the caller when all tract statuses are cached', () => {
    service.disadvantaged = { '01001020100': true, '01001020200': false }
    const statusReady = jasmine.createSpy('statusReady')

    service.checkDisadvantagedStatus(['01001020100', '01001020200']).subscribe(statusReady)

    expect(statusReady).toHaveBeenCalledTimes(1)
    http.expectNone('/api/v3/eeej/filter_disadvantaged_tracts/')
  })

  it('should complete without a request when there are no census tracts', () => {
    const complete = jasmine.createSpy('complete')

    service.checkDisadvantagedStatus([]).subscribe({ complete })

    expect(complete).toHaveBeenCalledTimes(1)
    http.expectNone('/api/v3/eeej/filter_disadvantaged_tracts/')
  })

  it('should propagate lookup errors without caching a negative status', () => {
    const error = jasmine.createSpy('error')
    service.checkDisadvantagedStatus(['01001020100']).subscribe({ error })

    http.expectOne('/api/v3/eeej/filter_disadvantaged_tracts/').flush('Lookup failed', { status: 500, statusText: 'Internal Server Error' })

    expect(error).toHaveBeenCalledTimes(1)
    expect(service.disadvantaged).toEqual({})
  })
})
