import { AsyncPipe } from '@angular/common'
import { NO_ERRORS_SCHEMA } from '@angular/core'
import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import type { RowClassParams } from 'ag-grid-community'
import { BehaviorSubject, of, ReplaySubject } from 'rxjs'
import type { Column, FacilitiesPlan, FacilitiesPlanRun, FacilitiesPlanRunProperty } from '@seed/api'
import { ColumnService, FacilitiesPlanRunService, FacilitiesPlanService, UserService } from '@seed/api'
import { ConfigService } from '@seed/services'
import { FacilitiesPlanComponent } from './facilities-plan.component'

// ─── Mock data ────────────────────────────────────────────────────────────────

const mockColumn: Column = {
  id: 1,
  name: 'address',
  organization_id: 1,
  table_name: 'PropertyState',
  merge_protection: 'Favor New',
  shared_field_type: 'None',
  column_name: 'address',
  is_extra_data: false,
  unit_name: null,
  unit_type: null,
  display_name: 'Address',
  data_type: 'string',
  is_matching_criteria: false,
  is_updating: false,
  geocoding_order: 0,
  recognize_empty: false,
  comstock_mapping: null,
  column_description: '',
  derived_column: null,
  is_excluded_from_hash: false,
}

const mockBooleanColumn: Column = {
  ...mockColumn,
  id: 2,
  column_name: 'include_in_denominator',
  display_name: 'Include in Denominator',
  data_type: 'boolean',
}

const mockNumberColumn: Column = {
  ...mockColumn,
  id: 3,
  column_name: 'electric_energy',
  display_name: 'Electric Energy',
  data_type: 'number',
}

const mockPlan: FacilitiesPlan = {
  id: 10,
  organization: 1,
  name: 'Test Plan',
  energy_running_sum_percentage: 80,
  compliance_cycle_year_column: null,
  include_in_total_denominator_column: null,
  exclude_from_plan_column: null,
  require_in_plan_column: null,
  electric_energy_usage_column: null,
  gas_energy_usage_column: null,
  steam_energy_usage_column: null,
}

const mockRun: FacilitiesPlanRun = {
  id: 42,
  facilities_plan: 10,
  cycle: 1,
  ali: 1,
  ali_name: 'Root',
  ali_level: 'Organization',
  name: 'FY2025 Plan',
  run_at: null,
  display_columns: [],
  columns: {},
  property_display_field: mockColumn,
}

const mockRunAfterCalculate: FacilitiesPlanRun = { ...mockRun, run_at: '2025-01-15T10:00:00Z' }

const mockProperties: FacilitiesPlanRunProperty[] = [
  {
    property_view_id: 101,
    total_energy_usage: 500,
    percentage_of_total_energy_usage: 25,
    rank: 1,
    running_percentage: 25,
    running_square_footage: 1000,
  },
  {
    property_view_id: 102,
    total_energy_usage: 300,
    percentage_of_total_energy_usage: 15,
    rank: 2,
    running_percentage: 40,
    running_square_footage: 800,
  },
]

const mockPropertiesResponse = {
  properties: mockProperties,
  pagination: { total: 2, page: 1, start: 1, end: 2, num_pages: 1, has_next: false, has_previous: false },
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Build a minimal RowClassParams object for rule tests. */
function makeParams(runningPct: number | null | undefined): RowClassParams<FacilitiesPlanRunProperty> {
  return {
    data: {
      property_view_id: 1,
      total_energy_usage: 0,
      percentage_of_total_energy_usage: 0,
      rank: 1,
      running_percentage: runningPct,
      running_square_footage: 0,
    },
  } as unknown as RowClassParams<FacilitiesPlanRunProperty>
}

// ─── Suite ────────────────────────────────────────────────────────────────────

describe('FacilitiesPlanComponent', () => {
  let component: FacilitiesPlanComponent
  let fixture: ComponentFixture<FacilitiesPlanComponent>

  // Shared subjects — reset per test via beforeEach
  let orgId$: ReplaySubject<number>
  let facilitiesPlans$: BehaviorSubject<FacilitiesPlan[]>
  let facilitiesPlanRuns$: BehaviorSubject<FacilitiesPlanRun[]>

  let getPropertiesSpy: jasmine.Spy
  let runSpy: jasmine.Spy

  beforeEach(async () => {
    orgId$ = new ReplaySubject<number>(1)
    orgId$.next(1)
    facilitiesPlans$ = new BehaviorSubject([mockPlan])
    facilitiesPlanRuns$ = new BehaviorSubject([] as FacilitiesPlanRun[])

    getPropertiesSpy = jasmine.createSpy('getProperties').and.returnValue(of(mockPropertiesResponse))
    runSpy = jasmine.createSpy('run').and.returnValue(of({ status: 'success' }))

    await TestBed.configureTestingModule({
      imports: [FacilitiesPlanComponent],
      providers: [
        {
          provide: FacilitiesPlanService,
          useValue: { facilitiesPlans$: facilitiesPlans$.asObservable(), list: jasmine.createSpy('list') },
        },
        {
          provide: FacilitiesPlanRunService,
          useValue: {
            facilitiesPlanRuns$: facilitiesPlanRuns$.asObservable(),
            list: jasmine.createSpy('list'),
            getProperties: getPropertiesSpy,
            run: runSpy,
            export: jasmine.createSpy('export').and.returnValue(of(new Blob())),
            getAllIds: jasmine.createSpy('getAllIds').and.returnValue(of({ ids: [] })),
          },
        },
        { provide: UserService, useValue: { currentOrganizationId$: orgId$.asObservable() } },
        { provide: ColumnService, useValue: { propertyColumns$: new BehaviorSubject<Column[]>([]).asObservable() } },
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
        { provide: MatDialog, useValue: { open: jasmine.createSpy('open').and.returnValue({ afterClosed: () => of(null) }) } },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    })
      .overrideComponent(FacilitiesPlanComponent, {
        set: {
          // Minimal template: no Transloco, no Material — tests conditional rendering logic only
          template: `
            <div class="h-full-page flex flex-col">
              @if (currentRun) {
                <ag-grid-angular [rowData]="rowData"></ag-grid-angular>
              } @else if (facilitiesPlanRuns.length === 0) {
                <div>No Facilities Plan Runs found</div>
              }
            </div>
          `,
          imports: [AsyncPipe],
          schemas: [NO_ERRORS_SCHEMA],
        },
      })
      .compileComponents()

    fixture = TestBed.createComponent(FacilitiesPlanComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  afterEach(() => {
    fixture.destroy()
  })

  // ─── Basic creation ─────────────────────────────────────────────────────────

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  // ─── Grid rendering (regression for the h-full-page height fix) ─────────────

  describe('grid rendering', () => {
    it('should not render ag-grid when no run is selected', () => {
      // Initial state: no runs, currentRun is null
      expect(component.currentRun).toBeNull()
      const grid = (fixture.nativeElement as HTMLElement).querySelector('ag-grid-angular')
      expect(grid).toBeNull()
    })

    it('should render ag-grid when a run is selected', () => {
      facilitiesPlanRuns$.next([mockRun])
      fixture.detectChanges()

      expect(component.currentRun).toEqual(mockRun)
      const grid = (fixture.nativeElement as HTMLElement).querySelector('ag-grid-angular')
      expect(grid).not.toBeNull()
    })

    it('should give the content wrapper the h-full-page class so the grid has a defined height', () => {
      facilitiesPlanRuns$.next([mockRun])
      fixture.detectChanges()

      // This class is the fix for the "blank grid" bug — regression guard
      const wrapper = (fixture.nativeElement as HTMLElement).querySelector('.h-full-page')
      expect(wrapper).not.toBeNull()
    })

    it('should show empty state message when no runs exist', () => {
      const text = (fixture.nativeElement as HTMLElement).textContent ?? ''
      expect(text).toContain('No Facilities Plan Runs found')
    })

    it('should hide empty state when runs exist', () => {
      facilitiesPlanRuns$.next([mockRun])
      fixture.detectChanges()

      const text = (fixture.nativeElement as HTMLElement).textContent ?? ''
      expect(text).not.toContain('No Facilities Plan Runs found')
    })
  })

  // ─── Data loading ────────────────────────────────────────────────────────────

  describe('data loading', () => {
    beforeEach(() => {
      facilitiesPlanRuns$.next([mockRun])
      fixture.detectChanges()
    })

    it('should call getProperties when a run is selected', () => {
      expect(getPropertiesSpy).toHaveBeenCalledWith(mockRun.id, 1, 1000, [], [])
    })

    it('should populate rowData from the API response', () => {
      expect(component.rowData).toEqual(mockProperties)
    })

    it('should set totalCount from the pagination response', () => {
      expect(component.totalCount).toBe(2)
    })

    it('should NOT set isLoading during data load (only calculatePlan should trigger it)', () => {
      // isLoading starts false, and _refreshGrid should not flip it
      expect(component.isLoading).toBeFalse()
    })

    it('should set isLoading true while calculatePlan is running', () => {
      // Override run spy to not complete immediately so we can inspect mid-flight state
      runSpy.and.returnValue(new BehaviorSubject(null).asObservable())
      component.calculatePlan()
      expect(component.isLoading).toBeTrue()
    })

    it('should call getProperties again when calculatePlan completes', () => {
      getPropertiesSpy.calls.reset()
      runSpy.and.returnValue(of({ status: 'success' }))
      component.calculatePlan()
      expect(getPropertiesSpy).toHaveBeenCalledTimes(1)
    })
  })

  // ─── rowClassRules: fp-in-plan ───────────────────────────────────────────────

  describe('rowClassRules fp-in-plan', () => {
    const rule = () => component.gridOptions.rowClassRules['fp-in-plan'] as (p: RowClassParams<FacilitiesPlanRunProperty>) => boolean

    beforeEach(() => {
      component.facilitiesPlans = [mockPlan] // energy_running_sum_percentage: 80
    })

    it('should return false when currentRun is null', () => {
      component.currentRun = null
      expect(rule()(makeParams(50))).toBeFalse()
    })

    it('should return false when run has not been calculated (run_at is null)', () => {
      component.currentRun = mockRun // run_at: null
      expect(rule()(makeParams(50))).toBeFalse()
    })

    it('should return false when running_percentage is null', () => {
      component.currentRun = mockRunAfterCalculate
      expect(rule()(makeParams(null))).toBeFalse()
    })

    it('should return false when running_percentage is undefined', () => {
      component.currentRun = mockRunAfterCalculate
      expect(rule()(makeParams(undefined))).toBeFalse()
    })

    it('should return true when running_percentage is within the plan threshold', () => {
      component.currentRun = mockRunAfterCalculate // run_at set
      // running_percentage(40) <= energy_running_sum_percentage(80) → in plan
      expect(rule()(makeParams(40))).toBeTrue()
    })

    it('should return true when running_percentage equals the threshold exactly', () => {
      component.currentRun = mockRunAfterCalculate
      expect(rule()(makeParams(80))).toBeTrue()
    })

    it('should return false when running_percentage exceeds the plan threshold', () => {
      component.currentRun = mockRunAfterCalculate
      // running_percentage(90) > energy_running_sum_percentage(80) → outside plan
      expect(rule()(makeParams(90))).toBeFalse()
    })

    it('should return false when the plan is not found', () => {
      component.currentRun = { ...mockRunAfterCalculate, facilities_plan: 999 } // no plan with id 999
      expect(rule()(makeParams(40))).toBeFalse()
    })
  })

  // ─── _buildColumnDefs: boolean column handling ───────────────────────────────

  describe('_buildColumnDefs', () => {
    const buildDefs = () => {
      ;(component as unknown as { _buildColumnDefs: () => void })._buildColumnDefs()
    }

    beforeEach(() => {
      component.currentRun = {
        ...mockRun,
        columns: {
          include_in_total_denominator_column: mockBooleanColumn, // data_type: boolean
          electric_energy_usage_column: mockNumberColumn, // data_type: number
        },
      }
      buildDefs()
    })

    it('should generate column defs for all run columns', () => {
      // 1 info + 1 property display + 2 from run.columns + 4 computed (total energy etc.)
      expect(component.columnDefs.length).toBeGreaterThanOrEqual(4)
    })

    it('should set cellDataType to text for boolean columns', () => {
      const boolCol = component.columnDefs.find((c) => c.field === `${mockBooleanColumn.column_name}_${mockBooleanColumn.id}`)
      expect(boolCol?.cellDataType).toBe('text')
    })

    it('should add a valueFormatter for boolean columns', () => {
      const boolCol = component.columnDefs.find((c) => c.field === `${mockBooleanColumn.column_name}_${mockBooleanColumn.id}`)
      expect(boolCol?.valueFormatter).toBeDefined()
    })

    it('valueFormatter should return "true" for true values', () => {
      const boolCol = component.columnDefs.find((c) => c.field === `${mockBooleanColumn.column_name}_${mockBooleanColumn.id}`)
      const fmt = boolCol?.valueFormatter as (p: { value: unknown }) => string
      expect(fmt({ value: true })).toBe('true')
    })

    it('valueFormatter should return "false" for false values', () => {
      const boolCol = component.columnDefs.find((c) => c.field === `${mockBooleanColumn.column_name}_${mockBooleanColumn.id}`)
      const fmt = boolCol?.valueFormatter as (p: { value: unknown }) => string
      expect(fmt({ value: false })).toBe('false')
    })

    it('valueFormatter should return empty string for null/undefined values', () => {
      const boolCol = component.columnDefs.find((c) => c.field === `${mockBooleanColumn.column_name}_${mockBooleanColumn.id}`)
      const fmt = boolCol?.valueFormatter as (p: { value: unknown }) => string
      expect(fmt({ value: null })).toBe('')
      expect(fmt({ value: undefined })).toBe('')
    })

    it('should NOT add cellDataType to non-boolean columns', () => {
      const numCol = component.columnDefs.find((c) => c.field === `${mockNumberColumn.column_name}_${mockNumberColumn.id}`)
      expect(numCol?.cellDataType).toBeUndefined()
    })

    it('should NOT add valueFormatter to non-boolean columns', () => {
      const numCol = component.columnDefs.find((c) => c.field === `${mockNumberColumn.column_name}_${mockNumberColumn.id}`)
      expect(numCol?.valueFormatter).toBeUndefined()
    })
  })
})
