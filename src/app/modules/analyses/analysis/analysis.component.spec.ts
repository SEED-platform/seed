import { CommonModule } from '@angular/common'
import { NO_ERRORS_SCHEMA } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router'
import type { CellClickedEvent } from 'ag-grid-community'
import { of } from 'rxjs'
import type { AnalysesMessage, Analysis, View } from '@seed/api'
import { AnalysisService, CycleService, MediaService, OrganizationService, UserService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { AnalysisComponent } from './analysis.component'

const failedAnalysis = { id: 3, name: 'Savings', service: 'BETTER', status: 'Failed', configuration: {} } as Analysis
const failedMessage = { id: 1, analysis: 3, analysis_property_view: null, user_message: 'No properties met the requirements' } as AnalysesMessage

describe('AnalysisComponent', () => {
  const configure = (providers: { analysisService?: object; mediaService?: object; userService?: object }) => {
    return TestBed.configureTestingModule({
      imports: [AnalysisComponent],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '3' }) } } },
        { provide: AnalysisService, useValue: providers.analysisService ?? {} },
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: CycleService, useValue: { cycles$: of([]) } },
        { provide: MatDialog, useValue: {} },
        { provide: MediaService, useValue: providers.mediaService ?? {} },
        { provide: OrganizationService, useValue: {} },
        { provide: Router, useValue: {} },
        { provide: SnackBarService, useValue: {} },
        { provide: UserService, useValue: providers.userService ?? {} },
      ],
    })
  }

  // Render the template without the page, grid, and Material components
  const renderAnalysis = async (views: View[]) => {
    const analysisService = {
      analysis$: of(failedAnalysis),
      views$: of(views),
      messages$: of([failedMessage]),
      originalViews$: of(null),
      getAnalysis: jasmine.createSpy('getAnalysis'),
      getAnalysisViews: jasmine.createSpy('getAnalysisViews'),
      getMessages: jasmine.createSpy('getMessages'),
      getAnalysisDescription: () => 'The BETTER analysis',
      getRunDuration: () => '',
    }
    await configure({ analysisService, userService: { currentOrganizationId$: of(1) } })
      .overrideComponent(AnalysisComponent, { set: { imports: [CommonModule], schemas: [NO_ERRORS_SCHEMA] } })
      .compileComponents()
    const fixture = TestBed.createComponent(AnalysisComponent)
    fixture.detectChanges()
    return fixture
  }

  it('renders an analysis without views, e.g., one that failed', async () => {
    const fixture = await renderAnalysis([])

    const element = fixture.nativeElement as HTMLElement
    expect(fixture.componentInstance.analysis).toBe(failedAnalysis)
    expect(element.textContent).toContain('BETTER Analysis')
    expect(element.textContent).toContain('No properties met the requirements')
    // Only the analysis grid, which shows its status
    const grids = element.querySelectorAll<HTMLElement & { rowData: Analysis[] }>('ag-grid-angular')
    expect(grids.length).toBe(1)
    expect(grids[0].rowData).toEqual([failedAnalysis])
  })

  it('renders an analysis without showing views from another analysis', async () => {
    const otherView = { id: 8, analysis: 4, output_files: [] } as View
    const fixture = await renderAnalysis([otherView])

    const element = fixture.nativeElement as HTMLElement
    expect(fixture.componentInstance.analysis).toBe(failedAnalysis)
    expect(fixture.componentInstance.gridViews).toEqual([])
    expect(element.querySelectorAll('ag-grid-angular').length).toBe(1)
  })

  it('downloads a run result with the media service', async () => {
    const download = jasmine.createSpy('download').and.returnValue(of(undefined))
    await configure({ mediaService: { download } })
      .overrideComponent(AnalysisComponent, { set: { template: '', imports: [] } })
      .compileComponents()
    const component = TestBed.createComponent(AnalysisComponent).componentInstance

    const target = document.createElement('span')
    target.setAttribute('data-action', 'download')
    const file = '/api/v3/media/analysis_output_files/report.html'
    const data = { id: 7, output_files: [{ id: 11, analysis_property_view: 7, content_type: 'html', file }] } as View
    component.onCellClicked({ colDef: { field: 'results' }, data, event: { target } } as unknown as CellClickedEvent)

    expect(download).toHaveBeenCalledOnceWith(file)
  })
})
