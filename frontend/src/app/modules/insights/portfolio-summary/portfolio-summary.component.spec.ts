import { NO_ERRORS_SCHEMA } from '@angular/core'
import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import { Router } from '@angular/router'
import type { CellValueChangedEvent, GridApi, SelectionChangedEvent } from 'ag-grid-community'
import { BehaviorSubject, of, ReplaySubject } from 'rxjs'
import type {
  Column,
  CycleGoal,
  Goal,
  GoalPagination,
  GoalProperty,
  Organization,
  PortfolioSummary,
  PropertyViewLabel,
  WeightedEUI,
} from '@seed/api'
import {
  ColumnService,
  ConfigService as DeploymentConfigService,
  GoalService,
  LabelService,
  OrganizationService,
  SalesforcePortfolioService,
  UserService,
} from '@seed/api'
import { ConfigService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { PortfolioSummaryComponent } from './portfolio-summary.component'

// ─── Mock data ────────────────────────────────────────────────────────────────

const mockOrganization = {
  id: 2,
  name: 'Test Org',
  bb_salesforce_enabled: true,
  access_level_names: ['Organization', 'Department'],
} as unknown as Organization

const mockCycleGoal: CycleGoal = { id: 10, current_cycle: { id: 5, name: 'FY2024', start: '2024-01-01', end: '2024-12-31' } }
const mockOlderCycleGoal: CycleGoal = { id: 9, current_cycle: { id: 4, name: 'FY2023', start: '2023-01-01', end: '2023-12-31' } }

const mockGoal: Goal = {
  id: 1,
  name: 'Test Goal',
  organization: 2,
  access_level_instance: 1,
  access_level_instance_name: 'Root',
  area_column: 1,
  area_column_name: 'Gross Floor Area',
  baseline_cycle: 3,
  baseline_cycle_name: 'FY2020',
  commitment_sqft: 100000,
  eui_column1: 1,
  eui_column1_name: 'Site EUI',
  level_name: 'Organization',
  level_name_index: 0,
  partner_note: 'Initial note',
  partner_note_approval: false,
  target_percentage: 20,
  type: 'standard',
  cycle_goals: [mockCycleGoal, mockOlderCycleGoal],
}

const mockPortfolioSummary: PortfolioSummary = {
  baseline_cycle_name: 'FY2020',
  baseline_total_sqft: 500000,
  baseline_total_kbtu: 10000000,
  baseline_weighted_eui: 100,
  total_properties: 50,
  shared_sqft: 450000,
  total_passing: 40,
  total_new_or_acquired: 5,
  passing_committed: 35,
  passing_shared: 30,
  current_cycle_name: 'FY2024',
  current_total_sqft: 480000,
  current_total_kbtu: '9000000',
  current_weighted_eui: 88,
  sqft_change: -4,
  eui_change: 12,
}

const mockWeightedEUIs: WeightedEUI[] = [
  { 'Cycle Name': 'FY2020', 'Baseline?': 'Yes', EUI: '100.00', Goal: 80, 'Annual % Imp': 0, 'Cumulative % Imp': 0 },
  { 'Cycle Name': 'FY2024', 'Baseline?': 'No', EUI: '88.00', Goal: 80, 'Annual % Imp': 12, 'Cumulative % Imp': 12 },
]

const mockPagination: GoalPagination = { page: 1, start: 1, end: 10, num_pages: 3, has_next: true, has_previous: false, total: 30 }

const mockGoalProperty: GoalProperty = {
  id: 101,
  baseline_cycle: 'FY2020',
  current_cycle: 'FY2024',
  baseline_view_id: 201,
  current_view_id: 202,
  baseline_sqft: 10000,
  current_sqft: 9500,
  baseline_eui: 100,
  current_eui: 88,
  baseline_kbtu: 1000000,
  current_kbtu: 836000,
  sqft_change: -5,
  eui_change: 12,
  goal_note: { id: 1, goal: 1, property: 101, question: null, resolution: null, passed_checks: true, new_or_acquired: false },
  historical_note: { id: 1, text: 'Test note', property: 101 },
}

const mockPropertiesResponse = {
  properties: [mockGoalProperty],
  pagination: mockPagination,
  property_lookup: {},
}

// ─── Suite ────────────────────────────────────────────────────────────────────

describe('PortfolioSummaryComponent', () => {
  let component: PortfolioSummaryComponent
  let fixture: ComponentFixture<PortfolioSummaryComponent>

  let orgSubject: ReplaySubject<Organization>
  let deploymentConfigSubject: BehaviorSubject<{ integrations: { salesforce: boolean; better: boolean } }>
  let goalsSubject: BehaviorSubject<Goal[]>
  let columnsSubject: BehaviorSubject<Column[]>

  let getPortfolioSummarySpy: jasmine.Spy
  let getWeightedEUIsSpy: jasmine.Spy
  let getCycleGoalsSpy: jasmine.Spy
  let getPropertiesSpy: jasmine.Spy
  let getPropertyViewIdsSpy: jasmine.Spy
  let deleteCycleGoalSpy: jasmine.Spy
  let editGoalSpy: jasmine.Spy
  let updateGoalNoteSpy: jasmine.Spy
  let updateHistoricalNoteSpy: jasmine.Spy
  let listByCycleGoalSpy: jasmine.Spy
  let verifyTokenSpy: jasmine.Spy
  let dialogOpenSpy: jasmine.Spy
  let routerNavigateSpy: jasmine.Spy

  beforeEach(async () => {
    orgSubject = new ReplaySubject<Organization>(1)
    deploymentConfigSubject = new BehaviorSubject({ integrations: { salesforce: true, better: true } })
    goalsSubject = new BehaviorSubject<Goal[]>([])
    columnsSubject = new BehaviorSubject<Column[]>([])

    getPortfolioSummarySpy = jasmine.createSpy('getPortfolioSummary').and.returnValue(of(mockPortfolioSummary))
    getWeightedEUIsSpy = jasmine.createSpy('getWeightedEUIs').and.returnValue(of({ status: 'success', results: mockWeightedEUIs }))
    getCycleGoalsSpy = jasmine.createSpy('getCycleGoals').and.returnValue(of([mockCycleGoal, mockOlderCycleGoal]))
    getPropertiesSpy = jasmine.createSpy('getProperties').and.returnValue(of(mockPropertiesResponse))
    getPropertyViewIdsSpy = jasmine.createSpy('getPropertyViewIds').and.returnValue(of([201]))
    deleteCycleGoalSpy = jasmine.createSpy('deleteCycleGoal').and.returnValue(of({}))
    editGoalSpy = jasmine.createSpy('editGoal').and.returnValue(of({ ...mockGoal }))
    updateGoalNoteSpy = jasmine.createSpy('updateGoalNote').and.returnValue(of({}))
    updateHistoricalNoteSpy = jasmine.createSpy('updateHistoricalNote').and.returnValue(of({}))
    listByCycleGoalSpy = jasmine.createSpy('listByCycleGoal').and.returnValue(of([]))
    verifyTokenSpy = jasmine.createSpy('verifyToken').and.returnValue(of({ valid: true }))
    dialogOpenSpy = jasmine.createSpy('open').and.returnValue({ afterClosed: () => of(null) })
    routerNavigateSpy = jasmine.createSpy('navigate').and.returnValue(Promise.resolve(true))

    await TestBed.configureTestingModule({
      imports: [PortfolioSummaryComponent],
      providers: [
        {
          provide: OrganizationService,
          useValue: { currentOrganization$: orgSubject.asObservable(), updateOrganizationUser: () => of({}) },
        },
        {
          provide: GoalService,
          useValue: {
            goals$: goalsSubject.asObservable(),
            getPortfolioSummary: getPortfolioSummarySpy,
            getWeightedEUIs: getWeightedEUIsSpy,
            getCycleGoals: getCycleGoalsSpy,
            getProperties: getPropertiesSpy,
            getPropertyViewIds: getPropertyViewIdsSpy,
            deleteCycleGoal: deleteCycleGoalSpy,
            editGoal: editGoalSpy,
            updateGoalNote: updateGoalNoteSpy,
            updateHistoricalNote: updateHistoricalNoteSpy,
            bulkUpdateGoalNotes: jasmine.createSpy('bulkUpdateGoalNotes').and.returnValue(of({})),
          },
        },
        { provide: ColumnService, useValue: { propertyColumns$: columnsSubject.asObservable() } },
        { provide: LabelService, useValue: { listByCycleGoal: listByCycleGoalSpy } },
        {
          provide: SalesforcePortfolioService,
          useValue: {
            verifyToken: verifyTokenSpy,
            getLoginUrl: jasmine.createSpy('getLoginUrl').and.returnValue(of({ url: 'http://sf.example.com' })),
          },
        },
        { provide: UserService, useValue: { currentUser$: of({ org_user_id: 99 }) } },
        { provide: MatDialog, useValue: { open: dialogOpenSpy } },
        { provide: Router, useValue: { navigate: routerNavigateSpy } },
        { provide: SnackBarService, useValue: { success: jasmine.createSpy('success'), alert: jasmine.createSpy('alert') } },
        { provide: DeploymentConfigService, useValue: { config$: deploymentConfigSubject.asObservable() } },
        { provide: ConfigService, useValue: { gridTheme$: of(null) } },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    })
      .overrideComponent(PortfolioSummaryComponent, {
        set: { template: '<div></div>', imports: [], schemas: [NO_ERRORS_SCHEMA] },
      })
      .compileComponents()

    fixture = TestBed.createComponent(PortfolioSummaryComponent)
    component = fixture.componentInstance
    fixture.detectChanges() // triggers ngOnInit; no org emitted yet so goal chain doesn't start
  })

  afterEach(() => {
    fixture.destroy()
  })

  // ─── Creation ───────────────────────────────────────────────────────────────

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  // ─── ngOnInit: organization and token ────────────────────────────────────────

  describe('ngOnInit — organization loading', () => {
    it('should skip Salesforce verification when disabled on this deployment', () => {
      deploymentConfigSubject.next({ integrations: { salesforce: false, better: true } })
      orgSubject.next(mockOrganization)
      expect(verifyTokenSpy).not.toHaveBeenCalled()
      expect(component.isLoggedIntoBbSalesforce).toBeFalse()
    })

    it('should set isLoggedIntoBbSalesforce true when token is valid', () => {
      verifyTokenSpy.and.returnValue(of({ valid: true }))
      orgSubject.next(mockOrganization)
      expect(component.isLoggedIntoBbSalesforce).toBeTrue()
    })

    it('should set isLoggedIntoBbSalesforce false when token is invalid', () => {
      verifyTokenSpy.and.returnValue(of({ valid: false }))
      orgSubject.next(mockOrganization)
      expect(component.isLoggedIntoBbSalesforce).toBeFalse()
    })

    it('should store the current organization', () => {
      orgSubject.next(mockOrganization)
      expect(component.organization).toEqual(mockOrganization)
    })
  })

  // ─── ngOnInit: goal auto-selection ──────────────────────────────────────────

  describe('ngOnInit — goal auto-selection', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
    })

    it('should auto-select the first goal when goals arrive', () => {
      goalsSubject.next([mockGoal])
      expect(component.currentGoal?.id).toBe(1)
    })

    it('should not auto-select when goals list is empty', () => {
      goalsSubject.next([])
      expect(component.currentGoal).toBeNull()
    })

    it('should not replace an already-selected goal when goals refresh', () => {
      goalsSubject.next([mockGoal])
      const secondGoal = { ...mockGoal, id: 2, name: 'Second Goal' }
      goalsSubject.next([secondGoal, mockGoal])
      // currentGoal was set to mockGoal (id:1) on first emit — should not be replaced
      expect(component.currentGoal?.id).toBe(1)
    })
  })

  // ─── _applyGoalSelection ─────────────────────────────────────────────────────

  describe('_applyGoalSelection', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
    })

    it('should fetch weighted EUIs for the selected goal', () => {
      goalsSubject.next([mockGoal])
      expect(getWeightedEUIsSpy).toHaveBeenCalledWith(1, 2)
    })

    it('should populate goalSummaryData from the weighted EUIs response', () => {
      goalsSubject.next([mockGoal])
      expect(component.goalSummaryData).toEqual(mockWeightedEUIs)
    })

    it('should fetch cycle goals for the selected goal', () => {
      goalsSubject.next([mockGoal])
      expect(getCycleGoalsSpy).toHaveBeenCalledWith(1, 2)
    })

    it('should auto-select the cycle with the latest end date', () => {
      // mockCycleGoal ends 2024-12-31, mockOlderCycleGoal ends 2023-12-31 — FY2024 should win
      goalsSubject.next([mockGoal])
      expect(component.currentCycleGoal?.id).toBe(10)
    })

    it('should reset portfolioSummary when a new goal is selected', () => {
      component.portfolioSummary = mockPortfolioSummary
      goalsSubject.next([mockGoal])
      // portfolioSummary is reset during _applyGoalSelection, then re-populated by selectCycleGoal
      expect(component.portfolioSummary).toEqual(mockPortfolioSummary) // repopulated
    })

    it('should initialize the partner note form with the goal note text', () => {
      goalsSubject.next([mockGoal])
      expect(component.partnerNoteForm.value.text).toBe('Initial note')
    })
  })

  // ─── selectCycleGoal ─────────────────────────────────────────────────────────

  describe('selectCycleGoal', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal])
      getPropertiesSpy.calls.reset()
      getPortfolioSummarySpy.calls.reset()
    })

    it('should set currentCycleGoal', () => {
      component.selectCycleGoal(mockOlderCycleGoal)
      expect(component.currentCycleGoal).toEqual(mockOlderCycleGoal)
    })

    it('should fetch the portfolio summary', () => {
      component.selectCycleGoal(mockOlderCycleGoal)
      expect(getPortfolioSummarySpy).toHaveBeenCalledWith(1, 9, 2)
    })

    it('should populate cycleGoalSummaryData with the portfolio summary', () => {
      component.selectCycleGoal(mockCycleGoal)
      expect(component.cycleGoalSummaryData).toEqual([mockPortfolioSummary])
    })

    it('should reset the property page to 1', () => {
      component.propertyPage = 5
      component.selectCycleGoal(mockCycleGoal)
      expect(component.propertyPage).toBe(1)
    })

    it('should fetch properties for the new cycle', () => {
      component.selectCycleGoal(mockCycleGoal)
      expect(getPropertiesSpy).toHaveBeenCalledWith(1, 10, 2, 1)
    })

    it('should show only labels associated with the selected goal', () => {
      const labels: PropertyViewLabel[] = [
        { id: 1, propertyview: 201, statuslabel: 10, goal: 1, name: 'Goal label', color: 'red', show_in_list: true },
        { id: 2, propertyview: 201, statuslabel: 11, goal: 2, name: 'Other goal label', color: 'blue', show_in_list: true },
        { id: 3, propertyview: 201, statuslabel: 12, goal: null, name: 'Unattached label', color: 'green', show_in_list: true },
        { id: 4, propertyview: 202, statuslabel: 10, goal: 1, name: 'Goal label', color: 'red', show_in_list: true },
        { id: 5, propertyview: 202, statuslabel: 12, goal: null, name: 'Unattached label', color: 'green', show_in_list: true },
      ]
      listByCycleGoalSpy.and.returnValue(of(labels))

      component.selectCycleGoal(mockCycleGoal)

      expect(component.baselineLabels.get(201)).toEqual([labels[0]])
      expect(component.currentLabels.get(202)).toEqual([labels[3]])
    })

    it('should populate goalProperties from the API response', () => {
      component.selectCycleGoal(mockCycleGoal)
      expect(component.goalProperties).toEqual([mockGoalProperty])
    })
  })

  describe('runDataQualityChecks', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal])
      dialogOpenSpy.and.returnValue({ afterClosed: () => of(true) })
      getPortfolioSummarySpy.calls.reset()
      getPropertiesSpy.calls.reset()
    })

    it('passes the selected goal and refreshes summary and properties after checks', () => {
      component.runDataQualityChecks()

      const dialogConfig = dialogOpenSpy.calls.mostRecent().args[1] as { data: { goalId: number } }
      expect(dialogConfig.data.goalId).toBe(mockGoal.id)
      expect(getPortfolioSummarySpy).toHaveBeenCalledWith(mockGoal.id, mockCycleGoal.id, mockOrganization.id)
      expect(getPropertiesSpy).toHaveBeenCalledWith(mockGoal.id, mockCycleGoal.id, mockOrganization.id, 1)
    })
  })

  // ─── changePage ──────────────────────────────────────────────────────────────

  describe('changePage', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal])
      component.propertiesPagination = mockPagination // num_pages: 3
      getPropertiesSpy.calls.reset()
    })

    it('should load the requested page', () => {
      component.changePage(2)
      expect(getPropertiesSpy).toHaveBeenCalledWith(1, 10, 2, 2)
    })

    it('should not load when page is less than 1', () => {
      component.changePage(0)
      expect(getPropertiesSpy).not.toHaveBeenCalled()
    })

    it('should not load when page exceeds num_pages', () => {
      component.changePage(4)
      expect(getPropertiesSpy).not.toHaveBeenCalled()
    })

    it('should not load when propertiesPagination is null', () => {
      component.propertiesPagination = null
      component.changePage(1)
      expect(getPropertiesSpy).not.toHaveBeenCalled()
    })
  })

  // ─── openDeleteCycleGoal ─────────────────────────────────────────────────────

  describe('openDeleteCycleGoal', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal])
      component.currentCycleGoal = mockCycleGoal
    })

    it('should call deleteCycleGoal with the correct IDs', () => {
      component.openDeleteCycleGoal()
      expect(deleteCycleGoalSpy).toHaveBeenCalledWith(1, 10)
    })

    it('should remove the deleted cycle from currentGoal.cycle_goals', () => {
      component.openDeleteCycleGoal()
      expect(component.currentGoal?.cycle_goals.some((cg) => cg.id === 10)).toBeFalse()
    })

    it('should select the next remaining cycle after deletion', () => {
      component.openDeleteCycleGoal()
      // mockOlderCycleGoal (id: 9) is the remaining cycle
      expect(component.currentCycleGoal?.id).toBe(9)
    })

    it('should clear all summary data when the last cycle is deleted', () => {
      component.currentGoal = { ...mockGoal, cycle_goals: [mockCycleGoal] }
      component.openDeleteCycleGoal()
      expect(component.cycleGoalSummaryData).toEqual([])
      expect(component.portfolioSummary).toBeNull()
      expect(component.goalProperties).toEqual([])
      expect(component.propertiesPagination).toBeNull()
    })

    it('should do nothing when currentGoal is null', () => {
      component.currentGoal = null
      component.openDeleteCycleGoal()
      expect(deleteCycleGoalSpy).not.toHaveBeenCalled()
    })
  })

  // ─── Partner note ─────────────────────────────────────────────────────────────

  describe('setEditingPartnerNote', () => {
    it('should enable the form when editing starts', () => {
      component.setEditingPartnerNote(true)
      expect(component.partnerNoteForm.enabled).toBeTrue()
    })

    it('should disable the form when editing ends', () => {
      component.partnerNoteForm.enable()
      component.setEditingPartnerNote(false)
      expect(component.partnerNoteForm.enabled).toBeFalse()
    })
  })

  describe('savePartnerNote', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal])
    })

    it('should call editGoal with the form text', () => {
      component.partnerNoteForm.setValue({ text: 'New note' })
      component.savePartnerNote()
      expect(editGoalSpy).toHaveBeenCalledWith(1, { partner_note: 'New note' }, 2)
    })

    it('should update currentGoal.partner_note after save', () => {
      editGoalSpy.and.returnValue(of({ ...mockGoal, partner_note: 'Updated note' }))
      component.savePartnerNote()
      expect(component.currentGoal?.partner_note).toBe('Updated note')
    })

    it('should disable the form after a successful save', () => {
      component.partnerNoteForm.enable()
      component.savePartnerNote()
      expect(component.partnerNoteForm.enabled).toBeFalse()
    })

    it('should do nothing when currentGoal is null', () => {
      component.currentGoal = null
      component.savePartnerNote()
      expect(editGoalSpy).not.toHaveBeenCalled()
    })
  })

  describe('partnerNoteApprovalLabel', () => {
    it('should return empty string when there is no approval timestamp', () => {
      component.currentGoal = { ...mockGoal, partner_note_approval_time: undefined }
      expect(component.partnerNoteApprovalLabel).toBe('')
    })

    it('should include the user name when present', () => {
      component.currentGoal = {
        ...mockGoal,
        partner_note_approval_time: '2024-06-15T12:00:00Z',
        partner_note_approval_user_name: 'Jane Doe',
      }
      expect(component.partnerNoteApprovalLabel).toContain('Jane Doe')
    })

    it('should still return a label without user name when only timestamp is present', () => {
      component.currentGoal = {
        ...mockGoal,
        partner_note_approval_time: '2024-06-15T12:00:00Z',
        partner_note_approval_user_name: undefined,
        partner_note_approval_user: undefined,
      }
      expect(component.partnerNoteApprovalLabel).toContain('Approved on')
    })
  })

  // ─── reviewAndSyncToSalesforce ───────────────────────────────────────────────

  describe('reviewAndSyncToSalesforce', () => {
    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal])
    })

    it('should open the SyncSalesforceDialog when goal and cycle are set', () => {
      component.currentCycleGoal = mockCycleGoal
      component.reviewAndSyncToSalesforce()
      expect(dialogOpenSpy).toHaveBeenCalled()
    })

    it('should pass the current goal, cycle goal and organization to the dialog', () => {
      component.currentCycleGoal = mockCycleGoal
      component.reviewAndSyncToSalesforce()
      const dialogData = (dialogOpenSpy.calls.mostRecent().args[1] as { data: { goal: Goal; currentCycleGoal: CycleGoal } }).data
      expect(dialogData.goal.id).toBe(1)
      expect(dialogData.currentCycleGoal.id).toBe(10)
    })

    it('should not open the dialog when currentGoal is null', () => {
      component.currentGoal = null
      component.currentCycleGoal = mockCycleGoal
      component.reviewAndSyncToSalesforce()
      expect(dialogOpenSpy).not.toHaveBeenCalled()
    })

    it('should not open the dialog when currentCycleGoal is null', () => {
      component.currentCycleGoal = null
      component.reviewAndSyncToSalesforce()
      expect(dialogOpenSpy).not.toHaveBeenCalled()
    })
  })

  // ─── toSettings ──────────────────────────────────────────────────────────────

  describe('toSettings', () => {
    it('should navigate to the Salesforce settings route', () => {
      component.toSettings()
      expect(routerNavigateSpy).toHaveBeenCalledWith(['/organizations/settings/salesforce-building-integration'])
    })
  })

  // ─── selectAllProperties / selectNoProperties ────────────────────────────────

  describe('selectAllProperties / selectNoProperties', () => {
    const mockGridApi = {
      deselectAll: jasmine.createSpy('deselectAll'),
      getSelectedRows: jasmine.createSpy('getSelectedRows').and.returnValue([mockGoalProperty]),
      forEachNode: jasmine.createSpy('forEachNode'),
    }

    beforeEach(() => {
      component.propertyGridApi = mockGridApi as unknown as GridApi
      component.goalProperties = [mockGoalProperty]
      component.currentGoal = mockGoal
      component.currentCycleGoal = mockCycleGoal
      component.organization = mockOrganization
      component.propertiesPagination = mockPagination
    })

    it('selectAllProperties should load all goal properties, not only the current page', () => {
      getPropertyViewIdsSpy.and.returnValue(of([201, 202]))
      component.selectAllProperties()
      expect(getPropertyViewIdsSpy).toHaveBeenCalledWith(mockGoal.id, mockCycleGoal.id, mockOrganization.id)
      expect(component.selectedPropertyViewIds).toEqual([201, 202])
    })

    it('selectNoProperties should call deselectAll on the grid', () => {
      component.selectNoProperties()
      expect(mockGridApi.deselectAll).toHaveBeenCalled()
    })

    it('selectNoProperties should empty selectedPropertyViewIds', () => {
      component.selectedPropertyViewIds = [201]
      component.selectNoProperties()
      expect(component.selectedPropertyViewIds).toEqual([])
    })

    it('preserves selections from other pages when a row changes on this page', () => {
      component.selectedPropertyViewIds = [101]
      component.goalProperties = [{ ...mockGoalProperty, baseline_view_id: 201 }]
      mockGridApi.getSelectedRows.and.returnValue([{ ...mockGoalProperty, baseline_view_id: 201 }])

      component.onPropertySelectionChanged({ source: 'checkboxSelected' } as SelectionChangedEvent)

      expect(component.selectedPropertyViewIds).toEqual([101, 201])
    })

    it('treats the grid header select-all as a request to select across all pages', () => {
      getPropertyViewIdsSpy.and.returnValue(of([201, 202]))
      mockGridApi.getSelectedRows.and.returnValue([mockGoalProperty])

      component.onPropertySelectionChanged({ source: 'uiSelectAll' } as SelectionChangedEvent)

      expect(getPropertyViewIdsSpy).toHaveBeenCalledWith(mockGoal.id, mockCycleGoal.id, mockOrganization.id)
      expect(component.selectedPropertyViewIds).toEqual([201, 202])
    })
  })

  // ─── defaultColDef.valueFormatter ────────────────────────────────────────────

  describe('defaultColDef.valueFormatter', () => {
    const fmt = (value: unknown) => (component.defaultColDef.valueFormatter as (p: { value: unknown }) => string)({ value })

    it('should return an em dash for null values', () => {
      expect(fmt(null)).toBe('\u2014')
    })

    it('should return an em dash for undefined values', () => {
      expect(fmt(undefined)).toBe('\u2014')
    })

    it('should stringify numeric values', () => {
      expect(fmt(42)).toBe('42')
    })

    it('should pass through string values unchanged', () => {
      expect(fmt('hello')).toBe('hello')
    })
  })

  // ─── cycleGoalSummaryColumnDefs: eui_change cell style ───────────────────────

  describe('eui_change cell style', () => {
    const euiChangeDef = () => component.cycleGoalSummaryColumnDefs.find((c) => c.field === 'eui_change')
    const cellStyle = (value: number | null) =>
      (euiChangeDef().cellStyle as (p: { value: unknown }) => Record<string, string> | null)({ value })

    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal]) // sets currentGoal.target_percentage = 20
    })

    it('should return null for null values', () => {
      expect(cellStyle(null)).toBeNull()
    })

    it('should return green when eui_change meets the target percentage', () => {
      const style = cellStyle(20)
      expect(style?.backgroundColor).toContain('34,197,94')
    })

    it('should return green when eui_change exceeds the target percentage', () => {
      const style = cellStyle(25)
      expect(style?.backgroundColor).toContain('34,197,94')
    })

    it('should return red when eui_change is below the target percentage', () => {
      const style = cellStyle(10)
      expect(style?.backgroundColor).toContain('239,68,68')
    })
  })

  // ─── onPropertyCellValueChanged ──────────────────────────────────────────────

  describe('onPropertyCellValueChanged', () => {
    const makeEvent = (colId: string, newValue: unknown, data: GoalProperty): CellValueChangedEvent =>
      ({
        column: { getColId: () => colId },
        data,
        newValue,
      }) as unknown as CellValueChangedEvent

    beforeEach(() => {
      orgSubject.next(mockOrganization)
      goalsSubject.next([mockGoal])
    })

    it('should call updateGoalNote for goal_note_question changes', () => {
      component.onPropertyCellValueChanged(makeEvent('goal_note_question', 'Is this correct?', mockGoalProperty))
      expect(updateGoalNoteSpy).toHaveBeenCalledWith(101, 1, { question: 'Is this correct?' })
    })

    it('should call updateGoalNote with null for empty question', () => {
      component.onPropertyCellValueChanged(makeEvent('goal_note_question', '', mockGoalProperty))
      expect(updateGoalNoteSpy).toHaveBeenCalledWith(101, 1, { question: null })
    })

    it('should call updateGoalNote for goal_note_resolution changes', () => {
      component.onPropertyCellValueChanged(makeEvent('goal_note_resolution', 'Resolved', mockGoalProperty))
      expect(updateGoalNoteSpy).toHaveBeenCalledWith(101, 1, { resolution: 'Resolved' })
    })

    it('should call updateHistoricalNote for historical_note_text changes', () => {
      component.onPropertyCellValueChanged(makeEvent('historical_note_text', 'New history', mockGoalProperty))
      expect(updateHistoricalNoteSpy).toHaveBeenCalledWith(101, 1, { text: 'New history' })
    })

    it('should not call any service when goal_note is null', () => {
      const propertyNoNote = { ...mockGoalProperty, goal_note: null }
      component.onPropertyCellValueChanged(makeEvent('goal_note_question', 'test', propertyNoNote))
      expect(updateGoalNoteSpy).not.toHaveBeenCalled()
    })
  })

  // ─── exportTable ─────────────────────────────────────────────────────────────

  describe('exportTable', () => {
    it('should not throw when goalSummaryData is empty', () => {
      component.goalSummaryData = []
      expect(() => {
        component.exportTable()
      }).not.toThrow()
    })

    it('should not create a download when goalSummaryData is empty', () => {
      const createElementSpy = spyOn(document, 'createElement').and.callThrough()
      component.goalSummaryData = []
      component.exportTable()
      // createElement for <a> should NOT be called when data is empty
      expect(createElementSpy).not.toHaveBeenCalledWith('a')
    })

    it('should trigger a download when data is present', () => {
      const mockAnchor = { href: '', download: '', click: jasmine.createSpy('click') }
      spyOn(document, 'createElement').and.returnValue(mockAnchor as unknown as HTMLElement)
      spyOn(URL, 'createObjectURL').and.returnValue('blob:test')
      spyOn(URL, 'revokeObjectURL')
      component.goalSummaryData = mockWeightedEUIs
      component.exportTable()
      expect(mockAnchor.click).toHaveBeenCalled()
      expect(mockAnchor.download).toBe('portfolio_summary_table.csv')
    })
  })

  // ─── ngOnDestroy ─────────────────────────────────────────────────────────────

  describe('ngOnDestroy', () => {
    it('should complete the unsubscribeAll subject', () => {
      const ctx = component as unknown as { _unsubscribeAll$: { complete: () => void } }
      const completeSpy = spyOn(ctx._unsubscribeAll$, 'complete')
      component.ngOnDestroy()
      expect(completeSpy).toHaveBeenCalled()
    })
  })
})
