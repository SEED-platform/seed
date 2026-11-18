import { provideHttpClient } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { firstValueFrom, of } from 'rxjs'
import { ErrorService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { OrganizationService } from '../organization'
import { UserService } from '../user'
import { AnalysisService } from './analysis.service'
import type { Analysis, AnalysisViews, ListAnalysesResponse, View } from './analysis.types'

const LIST_URL = '/api/v3/analyses/?organization_id=1&include_views=false'

const view = (file: string): View => ({
  id: 7,
  analysis: 3,
  cycle: 1,
  display_name: 'Building',
  output_files: [{ id: 11, analysis_property_view: 7, content_type: 'html', file }],
  parsed_results: {},
  property: 5,
  property_state: 9,
})

describe('AnalysisService', () => {
  let service: AnalysisService
  let http: HttpTestingController

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: UserService, useValue: { currentOrganizationId$: of(1) } },
        { provide: OrganizationService, useValue: {} },
        { provide: ErrorService, useValue: {} },
        { provide: SnackBarService, useValue: {} },
      ],
    })
    service = TestBed.inject(AnalysisService)
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
  })

  it('lists analyses without their views', async () => {
    const analyses = [{ id: 3, name: 'BETTER' } as Analysis]
    const response: ListAnalysesResponse = { status: 'success', analyses }
    http.expectOne(LIST_URL).flush(response)

    expect(await firstValueFrom(service.analyses$)).toEqual(analyses)
  })

  it("keeps an analysis's views when the analyses list loads after them", async () => {
    service.getAnalysisViews(1, 3)
    const analysisViews: AnalysisViews = {
      status: 'success',
      views: [view('/api/v3/media/analysis_output_files/report.html')],
      original_views: { 7: 5 },
    }
    http.expectOne('/api/v3/analyses/3/views?organization_id=1').flush(analysisViews)

    // e.g., a backend that ignores `include_views` returns the list endpoint's views, whose files are server paths
    const listResponse: ListAnalysesResponse = {
      status: 'success',
      analyses: [],
      views: [view('/seed/media/analysis_output_files/report.html')],
      original_views: { 7: 5 },
    }
    http.expectOne(LIST_URL).flush(listResponse)

    expect(await firstValueFrom(service.views$)).toEqual(analysisViews.views)
    expect(await firstValueFrom(service.originalViews$)).toEqual(analysisViews.original_views)
  })
})
