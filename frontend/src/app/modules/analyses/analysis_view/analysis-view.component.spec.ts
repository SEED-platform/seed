import { CommonModule } from '@angular/common'
import { NO_ERRORS_SCHEMA } from '@angular/core'
import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import { ActivatedRoute, convertToParamMap } from '@angular/router'
import { BehaviorSubject, defer, of, throwError } from 'rxjs'
import type { AnalysesMessage, Analysis, AnalysisView, View } from '@seed/api'
import { AnalysisService, CycleService, MediaService, OrganizationService, UserService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { AnalysisViewComponent } from './analysis-view.component'

const REPORT_URL = '/api/v3/media/analysis_output_files/report.html'
const IMAGE_URL = '/api/v3/media/analysis_output_files/plot.png'
const IMAGE_DATA_URL = `data:image/png;base64,${btoa('png')}`
const SRCDOC_BASE = '<base href="about:srcdoc">'

const testAnalysis = { id: 3, name: 'BETTER', service: 'BETTER' } as Analysis
const testView: View = {
  id: 7,
  analysis: 3,
  cycle: 1,
  display_name: 'Building',
  output_files: [
    { id: 11, analysis_property_view: 7, content_type: 'html', file: REPORT_URL },
    { id: 12, analysis_property_view: 7, content_type: 'PNG', file: IMAGE_URL },
    { id: 13, analysis_property_view: 7, content_type: 'BuildingSync', file: '/api/v3/media/analysis_output_files/building.xml' },
  ],
  parsed_results: {},
  property: 5,
  property_state: 9,
}

describe('AnalysisViewComponent', () => {
  let fixture: ComponentFixture<AnalysisViewComponent>
  let mediaService: jasmine.SpyObj<MediaService>
  let analysis$: BehaviorSubject<Analysis>
  let messages$: BehaviorSubject<AnalysesMessage[]>
  let view$: BehaviorSubject<View>
  let originalView$: BehaviorSubject<number>
  let getAnalysisView: jasmine.Spy

  const createComponent = async (initialAnalysis: Analysis = testAnalysis) => {
    analysis$ = new BehaviorSubject<Analysis>(initialAnalysis)
    messages$ = new BehaviorSubject<AnalysesMessage[]>([])
    view$ = new BehaviorSubject<View>(null)
    originalView$ = new BehaviorSubject<number>(null)
    // Like the service, update the shared streams when the request is made
    getAnalysisView = jasmine.createSpy('getAnalysisView').and.callFake(() =>
      defer(() => {
        view$.next(testView)
        originalView$.next(5)
        const response: AnalysisView = { status: 'success', view: testView, original_view: 5 }
        return of(response)
      }),
    )
    const analysisService = {
      analysis$,
      messages$,
      view$,
      originalView$,
      getAnalysis: jasmine.createSpy('getAnalysis'),
      getMessages: jasmine.createSpy('getMessages'),
      getAnalysisView,
    }

    await TestBed.configureTestingModule({
      imports: [AnalysisViewComponent],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '3', viewId: '7' }) } } },
        { provide: AnalysisService, useValue: analysisService },
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: CycleService, useValue: { cycles$: of([{ id: 1, name: '2024' }]) } },
        { provide: MediaService, useValue: mediaService },
        { provide: OrganizationService, useValue: { getViewDisplayField: () => of('Building') } },
        { provide: UserService, useValue: { currentOrganizationId$: new BehaviorSubject(1) } },
      ],
    })
      // Render the template's results without the page, grid, and Material components
      .overrideComponent(AnalysisViewComponent, { set: { imports: [CommonModule], schemas: [NO_ERRORS_SCHEMA] } })
      .compileComponents()

    fixture = TestBed.createComponent(AnalysisViewComponent)
    fixture.detectChanges()
  }

  const getReport = () => (fixture.nativeElement as HTMLElement).querySelector('iframe').srcdoc

  beforeEach(() => {
    mediaService = jasmine.createSpyObj<MediaService>('MediaService', ['download', 'getDataUrl', 'getText'])
    mediaService.download.and.returnValue(of(undefined))
    mediaService.getDataUrl.and.returnValue(of(IMAGE_DATA_URL))
    mediaService.getText.and.returnValue(of('<p>Report</p>'))
  })

  afterEach(() => {
    fixture.destroy()
  })

  it('fetches the HTML report and shows it in a sandbox without same-origin access', async () => {
    await createComponent()

    expect(mediaService.getText).toHaveBeenCalledOnceWith(REPORT_URL)
    const iframe = (fixture.nativeElement as HTMLElement).querySelector('iframe')
    expect(iframe.srcdoc).toBe(`${SRCDOC_BASE}<p>Report</p>`)
    expect(iframe.getAttribute('src')).toBeNull()
    const sandbox = iframe.getAttribute('sandbox')
    expect(sandbox).toContain('allow-scripts')
    expect(sandbox).not.toContain('allow-same-origin')
    expect(sandbox).not.toContain('allow-popups-to-escape-sandbox')
  })

  it("resolves the report's fragment links against the report, keeping its doctype first", async () => {
    const report = [
      '<!DOCTYPE html>',
      '<html lang="en"><head><meta charset="utf-8"><title>Report</title></head>',
      '<body><a href="#savings">Savings</a><h2 id="savings">Savings</h2></body></html>',
    ].join('\n')
    mediaService.getText.and.returnValue(of(report))
    await createComponent()

    const srcdoc = getReport()
    expect(srcdoc).toBe(report.replace('<head>', `<head>${SRCDOC_BASE}`))
    const parsed = new DOMParser().parseFromString(srcdoc, 'text/html')
    expect(parsed.compatMode).toBe('CSS1Compat')
    expect(parsed.head.firstElementChild.outerHTML).toBe(SRCDOC_BASE)
    expect(parsed.querySelector('a').href).toBe('about:srcdoc#savings')
  })

  it('adds the base after the doctype of a report without a head', async () => {
    mediaService.getText.and.returnValue(of('<!doctype html><header>Report</header>'))
    await createComponent()

    const srcdoc = getReport()
    expect(srcdoc).toBe(`<!doctype html>${SRCDOC_BASE}<header>Report</header>`)
    const parsed = new DOMParser().parseFromString(srcdoc, 'text/html')
    expect(parsed.compatMode).toBe('CSS1Compat')
    expect(parsed.head.firstElementChild.outerHTML).toBe(SRCDOC_BASE)
  })

  it('fetches images and shows them as data: URLs', async () => {
    await createComponent()

    expect(mediaService.getDataUrl).toHaveBeenCalledOnceWith(IMAGE_URL)
    const img = (fixture.nativeElement as HTMLElement).querySelector('img')
    expect(img.getAttribute('src')).toBe(IMAGE_DATA_URL)
  })

  it('fetches the files again only when they change', async () => {
    await createComponent()

    view$.next({ ...testView })
    expect(mediaService.getText).toHaveBeenCalledTimes(1)

    const newReportUrl = '/api/v3/media/analysis_output_files/new_report.html'
    view$.next({ ...testView, output_files: [{ ...testView.output_files[0], file: newReportUrl }] })
    expect(mediaService.getText).toHaveBeenCalledTimes(2)
    expect(mediaService.getText).toHaveBeenCalledWith(newReportUrl)
  })

  it('shows the other files when one fails to load', async () => {
    mediaService.getText.and.returnValue(throwError(() => new Error('Error fetching file')))
    await createComponent()

    const element = fixture.nativeElement as HTMLElement
    expect(element.querySelector('iframe')).toBeNull()
    expect(element.querySelector('img').getAttribute('src')).toBe(IMAGE_DATA_URL)
  })

  it('downloads output files with the media service', async () => {
    await createComponent()

    fixture.componentInstance.downloadOutputFile()

    expect(mediaService.download).toHaveBeenCalledOnceWith(REPORT_URL)
  })

  it('waits for its own analysis in the shared analysis stream', async () => {
    // e.g., the analysis viewed before this one
    await createComponent({ id: 9, name: 'EUI', service: 'EUI' } as Analysis)
    expect(getAnalysisView).not.toHaveBeenCalled()

    analysis$.next(testAnalysis)
    expect(getAnalysisView).toHaveBeenCalledTimes(1)
    expect(fixture.componentInstance.analysis).toBe(testAnalysis)
  })

  it('stops fetching its view once destroyed', async () => {
    await createComponent()
    expect(getAnalysisView).toHaveBeenCalledTimes(1)

    fixture.destroy()
    // E.g., the next analysis view page fetches the analysis and its messages
    analysis$.next({ ...testAnalysis })
    messages$.next([])

    expect(getAnalysisView).toHaveBeenCalledTimes(1)
  })

  it("ignores other analysis property views' responses in the shared view stream", async () => {
    await createComponent()

    const otherReportUrl = '/api/v3/media/analysis_output_files/other_report.html'
    const otherFile = { id: 21, analysis_property_view: 8, content_type: 'html', file: otherReportUrl }
    view$.next({ ...testView, id: 8, cycle: 2, output_files: [otherFile] })
    originalView$.next(6)

    const component = fixture.componentInstance
    expect(component.view).toBe(testView)
    expect(component.propertyViewId).toBe(5)
    expect(component.cycle).toEqual({ id: 1, name: '2024' })
    component.downloadOutputFile()
    expect(mediaService.download).toHaveBeenCalledOnceWith(REPORT_URL)
    expect(mediaService.getText).not.toHaveBeenCalledWith(otherReportUrl)
  })
})
