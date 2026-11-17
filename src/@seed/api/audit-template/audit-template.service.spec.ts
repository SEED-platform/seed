import { provideHttpClient } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { TestBed } from '@angular/core/testing'
import { firstValueFrom, of } from 'rxjs'
import { ErrorService } from '@seed/services/error/error.service'
import type { ProgressResponse } from '../progress'
import { UserService } from '../user'
import { AuditTemplateService } from './audit-template.service'

describe('AuditTemplateService', () => {
  let service: AuditTemplateService
  let http: HttpTestingController
  const progress = { progress_key: ':1:SEED:task:PROG:abc', progress: 0, status: 'not-started' } as ProgressResponse

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: UserService, useValue: { currentOrganizationId$: of(1) } },
        { provide: ErrorService, useValue: {} },
      ],
    })
    service = TestBed.inject(AuditTemplateService)
    http = TestBed.inject(HttpTestingController)
    // the report types and configs that the service loads when it's created
    http.expectOne('/api/v3/audit_template/report_types/').flush({ status: 'success', data: [] })
    http.expectOne('/api/v3/audit_template_configs/?organization_id=1').flush({ status: 'success', data: [] })
  })

  afterEach(() => {
    http.verify()
  })

  it('updates properties from Audit Template submissions with a PUT, the only method the endpoint accepts', async () => {
    const response = firstValueFrom(service.batchGetCitySubmissionXml(1, [5, 6], 2))

    const request = http.expectOne('/api/v3/audit_template/batch_get_city_submission_xml/?organization_id=1')
    expect(request.request.method).toBe('PUT')
    expect(request.request.body).toEqual({ view_ids: [5, 6], default_cycle: 2 })
    request.flush(progress)
    expect(await response).toEqual(progress)
  })

  it('exports properties to Audit Template with a POST', async () => {
    const response = firstValueFrom(service.batchExportToAuditTemplate(1, [5, 6]))

    const request = http.expectOne('/api/v3/audit_template/batch_export_to_audit_template/?organization_id=1')
    expect(request.request.method).toBe('POST')
    expect(request.request.body).toEqual({ property_view_ids: [5, 6] })
    request.flush(progress)
    expect(await response).toEqual(progress)
  })
})
