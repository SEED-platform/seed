import { AsyncPipe, CommonModule } from '@angular/common'
import type { ElementRef, OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import type { MatSelectChange } from '@angular/material/select'
import { Router, RouterLink } from '@angular/router'
import { TranslocoDirective } from '@jsverse/transloco'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellClickedEvent, CellValueChangedEvent, ColDef, GridApi, GridReadyEvent, SelectionChangedEvent } from 'ag-grid-community'
import { Chart } from 'chart.js/auto'
import annotationPlugin from 'chartjs-plugin-annotation'
import { combineLatest, filter, finalize, map, of, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type {
  Column,
  CycleGoal,
  Goal,
  GoalNote,
  GoalPagination,
  GoalProperty,
  Organization,
  OrganizationUserSettings,
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
import { NotFoundComponent, PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { DQCStartModalComponent } from 'app/modules/data-quality/start-modal.component'
import { LabelsModalComponent } from 'app/modules/inventory/actions'
import { AddCycleDialogComponent } from './add-cycle-dialog'
import { BulkEditGoalNotesModalComponent } from './bulk-edit-goal-notes-modal.component'
import { ConfigureGoalsDialogComponent } from './configure-goals-dialog'
import { PortfolioSummaryHeaderMenuComponent } from './portfolio-summary-header-menu.component'
import { PortfolioSummaryLabelHeaderComponent } from './portfolio-summary-label-header.component'
import type { AddCycleData, ConfigureGoalsData, LabelColumnKey, SyncSalesforceData } from './portfolio-summary.types'
import { SyncSalesforceDialogComponent } from './sync-salesforce-dialog'

Chart.register(annotationPlugin)

const QUESTION_OPTIONS = [
  '',
  'Is this a new construction or acquisition?',
  'Do you have data to report?',
  'Is this value correct?',
  'Are these values correct?',
  'Other or multiple flags; explain in Additional Notes field',
]

const LABEL_COLOR_MAP: Record<string, string> = {
  red: '#b91c1c',
  orange: '#fb923c',
  gray: '#57534e',
  green: '#15803d',
  blue: '#1d4ed8',
  'light blue': '#0891b2',
  white: '#e5e7eb',
}

@Component({
  selector: 'seed-portfolio-summary',
  templateUrl: './portfolio-summary.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [
    AgGridAngular,
    AsyncPipe,
    CommonModule,
    FormsModule,
    MaterialImports,
    NotFoundComponent,
    PageComponent,
    ReactiveFormsModule,
    RouterLink,
    SharedImports,
    TranslocoDirective,
  ],
})
export class PortfolioSummaryComponent implements OnInit, OnDestroy {
  @ViewChild('canvas') canvas!: ElementRef<HTMLCanvasElement>

  private _columnService = inject(ColumnService)
  private _deploymentConfigService = inject(DeploymentConfigService)
  private _goalService = inject(GoalService)
  private _labelService = inject(LabelService)
  private _matDialog = inject(MatDialog)
  private _organizationService = inject(OrganizationService)
  private _router = inject(Router)
  private _salesforcePortfolioService = inject(SalesforcePortfolioService)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _propertyColumns: Column[] = []
  private _orgUserId: number | null = null
  private _userSettings: OrganizationUserSettings = {}

  readonly gridTheme$ = inject(ConfigService).gridTheme$
  readonly defaultColDef: ColDef = {
    suppressMovable: true,
    floatingFilter: true,
    valueFormatter: (params) => {
      const v = params.value as string | number | null | undefined
      return v === null || v === undefined ? '\u2014' : String(v)
    },
  }

  isLoggedIntoBbSalesforce = false
  salesforceEnabled = true
  goals: Goal[] = []
  currentGoal: Goal | null = null
  goalSearchCtrl = new FormControl('')
  currentCycleGoal: CycleGoal | null = null
  portfolioSummary: PortfolioSummary | null = null
  organization: Organization

  // Partner note
  partnerNoteForm = new FormGroup({
    text: new FormControl<string | null>({ value: '', disabled: true }),
  })

  // Cycle goal summary grid (1-row baseline vs current comparison)
  cycleGoalSummaryData: PortfolioSummary[] = []
  cycleGoalSummaryColumnDefs: ColDef[] = [
    {
      headerName: 'Baseline Cycle',
      field: 'baseline_cycle_name',
      headerStyle: { backgroundColor: 'rgba(234,179,8,0.35)' },
      cellStyle: { backgroundColor: 'rgba(234,179,8,0.15)' },
    },
    {
      headerName: 'Baseline Area (sq ft)',
      field: 'baseline_total_sqft',
      headerStyle: { backgroundColor: 'rgba(234,179,8,0.35)' },
      cellStyle: { backgroundColor: 'rgba(234,179,8,0.15)' },
    },
    {
      headerName: 'Baseline kBTU',
      field: 'baseline_total_kbtu',
      headerStyle: { backgroundColor: 'rgba(234,179,8,0.35)' },
      cellStyle: { backgroundColor: 'rgba(234,179,8,0.15)' },
    },
    {
      headerName: 'Baseline EUI',
      field: 'baseline_weighted_eui',
      headerStyle: { backgroundColor: 'rgba(234,179,8,0.35)' },
      cellStyle: { backgroundColor: 'rgba(234,179,8,0.15)' },
    },
    {
      headerName: 'Current Cycle',
      field: 'current_cycle_name',
      headerStyle: { backgroundColor: 'rgba(239,68,68,0.35)' },
      cellStyle: { backgroundColor: 'rgba(239,68,68,0.15)' },
    },
    {
      headerName: 'Current Area (sq ft)',
      field: 'current_total_sqft',
      headerStyle: { backgroundColor: 'rgba(239,68,68,0.35)' },
      cellStyle: { backgroundColor: 'rgba(239,68,68,0.15)' },
    },
    {
      headerName: 'Current kBTU',
      field: 'current_total_kbtu',
      headerStyle: { backgroundColor: 'rgba(239,68,68,0.35)' },
      cellStyle: { backgroundColor: 'rgba(239,68,68,0.15)' },
    },
    {
      headerName: 'Current EUI',
      field: 'current_weighted_eui',
      headerStyle: { backgroundColor: 'rgba(239,68,68,0.35)' },
      cellStyle: { backgroundColor: 'rgba(239,68,68,0.15)' },
    },
    { headerName: 'Area % Change', field: 'sqft_change' },
    {
      headerName: 'EUI % Improvement',
      field: 'eui_change',
      cellStyle: (params) => {
        const value = params.value as number | null
        if (value === null || value === undefined) return null
        return value >= (this.currentGoal?.target_percentage ?? 0)
          ? { backgroundColor: 'rgba(34,197,94,0.30)' }
          : { backgroundColor: 'rgba(239,68,68,0.30)' }
      },
    },
  ]

  cycleGoalSummaryDefaultColDef: ColDef = { ...this.defaultColDef, floatingFilter: false }

  // Goal summary EUI table
  goalSummaryData: WeightedEUI[] = []
  goalSummaryColumnDefs: ColDef[] = [
    { field: 'Cycle Name', headerName: 'Cycle Name' },
    { field: 'Baseline?', headerName: 'Baseline?' },
    { field: 'EUI', headerName: 'EUI', valueFormatter: (p) => (p.value != null ? Number(p.value).toFixed(2) : '') },
    { field: 'Goal', headerName: 'Goal', valueFormatter: (p) => (p.value != null ? Number(p.value).toFixed(2) : '') },
    { field: 'Annual % Imp', headerName: 'Annual % Imp', valueFormatter: (p) => (p.value != null ? Number(p.value).toFixed(2) : '') },
    {
      field: 'Cumulative % Imp',
      headerName: 'Cumulative % Imp',
      valueFormatter: (p) => (p.value != null ? Number(p.value).toFixed(2) : ''),
    },
  ]

  // Property grid
  goalProperties: GoalProperty[] = []
  propertiesPagination: GoalPagination | null = null
  propertyPage = 1
  propertyGridApi: GridApi | null = null
  selectedPropertyViewIds: number[] = []
  isSelectingAllProperties = false
  propertyColumnDefs: ColDef[] = []
  private _selectionRequestId = 0
  private _syncingPropertySelection = false

  // Label columns
  baselineLabels = new Map<number, PropertyViewLabel[]>()
  currentLabels = new Map<number, PropertyViewLabel[]>()
  labelsExpanded: Record<LabelColumnKey, boolean> = { baseline: false, current: false }
  showAccessLevelInstances = false
  readonly propertyGridContext = {
    labelsExpanded: this.labelsExpanded,
    toggleLabels: (key: LabelColumnKey) => {
      this.toggleLabels(key)
    },
  }

  chart: Chart<'bar', string[], string> | null = null
  showDQBanner = true

  ngOnInit(): void {
    combineLatest([this._organizationService.currentOrganization$, this._deploymentConfigService.config$])
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(([organization, config]) => {
          this.organization = organization
          this.salesforceEnabled = config.integrations.salesforce
          return this.salesforceEnabled && this.organization.bb_salesforce_enabled
            ? this._salesforcePortfolioService.verifyToken(this.organization.id)
            : of({ valid: false })
        }),
      )
      .subscribe((r) => {
        this.isLoggedIntoBbSalesforce = r.valid
      })

    this._columnService.propertyColumns$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((columns) => {
      this._propertyColumns = columns
      this._buildPropertyColumnDefs()
    })

    // Load user settings first, then subscribe to goals so savedGoalId is available when goals arrive
    this._userService.currentUser$
      .pipe(
        take(1),
        switchMap((currentUser) => {
          this._orgUserId = currentUser.org_user_id
          this._userSettings = currentUser.settings ?? {}
          return this._goalService.goals$
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe((goals) => {
        this.goals = goals
        if (!this.currentGoal && goals.length) {
          const savedId = this._userSettings?.insights?.portfolioSummary?.goalId
          const savedGoal = savedId ? goals.find((g) => g.id === savedId) : null
          this._applyGoalSelection((savedGoal ?? goals[0]).id)
        }
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
    this.chart?.destroy()
  }

  // ─── Dialog openers ───────────────────────────────────────────────

  openConfigureGoals(): void {
    this._matDialog.open(ConfigureGoalsDialogComponent, {
      autoFocus: false,
      disableClose: true,
      width: '50rem',
      data: {
        goals: this.goals,
        isLoggedIntoBbSalesforce: this.isLoggedIntoBbSalesforce,
        bb_salesforce_enabled: this.organization.bb_salesforce_enabled,
      } satisfies ConfigureGoalsData,
    })
  }

  openAddCycle(): void {
    const dialogRef = this._matDialog.open(AddCycleDialogComponent, {
      autoFocus: false,
      disableClose: true,
      data: { currentGoal: this.currentGoal, isLoggedIntoBbSalesforce: this.isLoggedIntoBbSalesforce } satisfies AddCycleData,
    })
    dialogRef.afterClosed().subscribe((newCycleGoal?: CycleGoal) => {
      if (newCycleGoal && this.currentGoal) {
        this._goalService
          .getCycleGoals(this.currentGoal.id, this.organization.id)
          .pipe(takeUntil(this._unsubscribeAll$))
          .subscribe((cycleGoals) => {
            if (this.currentGoal) this.currentGoal = { ...this.currentGoal, cycle_goals: cycleGoals }
          })
      }
    })
  }

  openEditCycleGoal(): void {
    if (!this.currentGoal || !this.currentCycleGoal) return
    const dialogRef = this._matDialog.open(AddCycleDialogComponent, {
      autoFocus: false,
      disableClose: true,
      data: {
        currentGoal: this.currentGoal,
        isLoggedIntoBbSalesforce: this.isLoggedIntoBbSalesforce,
        existingCycleGoal: this.currentCycleGoal,
      } satisfies AddCycleData,
    })
    dialogRef.afterClosed().subscribe((updatedCycleGoal?: CycleGoal) => {
      if (updatedCycleGoal && this.currentGoal) {
        this._goalService
          .getCycleGoals(this.currentGoal.id, this.organization.id)
          .pipe(takeUntil(this._unsubscribeAll$))
          .subscribe((cycleGoals) => {
            if (this.currentGoal) this.currentGoal = { ...this.currentGoal, cycle_goals: cycleGoals }
            const updated = cycleGoals.find((cg) => cg.id === updatedCycleGoal.id) ?? cycleGoals[0] ?? null
            if (updated) this.selectCycleGoal(updated)
          })
      }
    })
  }

  openDeleteCycleGoal(): void {
    if (!this.currentGoal || !this.currentCycleGoal) return
    const cycleGoalId = this.currentCycleGoal.id
    this._goalService
      .deleteCycleGoal(this.currentGoal.id, cycleGoalId)
      .pipe(take(1))
      .subscribe(() => {
        if (!this.currentGoal) return
        const remaining = this.currentGoal.cycle_goals.filter((cg) => cg.id !== cycleGoalId)
        this.currentGoal = { ...this.currentGoal, cycle_goals: remaining }
        this.currentCycleGoal = remaining[0] ?? null
        if (this.currentCycleGoal) {
          this.selectCycleGoal(this.currentCycleGoal)
        } else {
          this.cycleGoalSummaryData = []
          this.portfolioSummary = null
          this.goalProperties = []
          this.propertiesPagination = null
        }
      })
  }

  // ─── Selectors ──────────────────────────────────────────────────────

  get filteredGoals(): Goal[] {
    const search = (this.goalSearchCtrl.value ?? '').toLowerCase()
    return search ? this.goals.filter((g) => g.name.toLowerCase().includes(search)) : this.goals
  }

  selectGoal(event: MatSelectChange): void {
    if (event.value == null) return
    this._applyGoalSelection(event.value as number)
  }

  onGoalDropdownOpened(opened: boolean): void {
    if (opened) this.goalSearchCtrl.setValue('')
  }

  selectCycleGoal(cycleGoal: CycleGoal): void {
    this.selectNoProperties()
    this.currentCycleGoal = cycleGoal
    this.propertyPage = 1

    if (!this.currentGoal) return
    this._goalService
      .getPortfolioSummary(this.currentGoal.id, cycleGoal.id, this.organization.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((portfolioSummary) => {
        this.cycleGoalSummaryData = [portfolioSummary]
        this.portfolioSummary = portfolioSummary
      })

    this._loadProperties(1)
    this._loadLabels(cycleGoal)
  }

  // ─── Property grid ───────────────────────────────────────────────

  onPropertyGridReady(event: GridReadyEvent): void {
    this.propertyGridApi = event.api
    this.propertyGridApi.addEventListener('cellClicked', this.onPropertyCellClicked.bind(this) as (event: CellClickedEvent) => void)
    this._syncPropertyGridSelection()
  }

  onPropertyCellClicked(event: CellClickedEvent): void {
    if (event.colDef.field !== 'baseline_view_id') return
    const target = event.event?.target as HTMLElement
    if (target?.getAttribute('data-action') !== 'detail') return
    const viewId = (event.data as GoalProperty).baseline_view_id
    if (viewId != null) void this._router.navigate(['/properties', viewId])
  }

  onPropertyCellValueChanged(event: CellValueChangedEvent): void {
    const row = event.data as GoalProperty
    const colId = event.column.getColId()
    if (colId === 'goal_note_question' || colId === 'goal_note_resolution') {
      if (!row.goal_note) return
      const field = colId === 'goal_note_question' ? 'question' : 'resolution'
      const value = (event.newValue as string) || null
      this._goalService
        .updateGoalNote(row.id, row.goal_note.id, { [field]: value })
        .pipe(take(1))
        .subscribe()
    } else if (colId === 'historical_note_text') {
      if (!row.historical_note) return
      this._goalService
        .updateHistoricalNote(row.id, row.historical_note.id, { text: (event.newValue as string) ?? '' })
        .pipe(take(1))
        .subscribe()
    } else if (colId === 'goal_note_passed_checks' || colId === 'goal_note_new_or_acquired') {
      if (!row.goal_note) return
      const field = colId === 'goal_note_passed_checks' ? 'passed_checks' : 'new_or_acquired'
      this._goalService
        .updateGoalNote(row.id, row.goal_note.id, { [field]: event.newValue as boolean })
        .pipe(take(1))
        .subscribe(() => {
          this._reloadPortfolioSummary()
        })
    }
  }

  changePage(page: number): void {
    if (!this.propertiesPagination) return
    if (page < 1 || page > this.propertiesPagination.num_pages) return
    this.propertyPage = page
    this._loadProperties(page)
  }

  selectAllProperties(): void {
    if (!this.currentGoal || !this.currentCycleGoal || !this.propertiesPagination?.total || this.isSelectingAllProperties) return

    const requestId = ++this._selectionRequestId
    this.isSelectingAllProperties = true
    this._goalService
      .getPropertyViewIds(this.currentGoal.id, this.currentCycleGoal.id, this.organization.id)
      .pipe(
        take(1),
        takeUntil(this._unsubscribeAll$),
        tap((propertyViewIds) => {
          if (requestId !== this._selectionRequestId) return
          this.selectedPropertyViewIds = propertyViewIds
          this._syncPropertyGridSelection()
        }),
        finalize(() => {
          if (requestId === this._selectionRequestId) this.isSelectingAllProperties = false
        }),
      )
      .subscribe()
  }

  selectNoProperties(): void {
    this._selectionRequestId += 1
    this.isSelectingAllProperties = false
    this.selectedPropertyViewIds = []
    this._syncingPropertySelection = true
    try {
      this.propertyGridApi?.deselectAll()
    } finally {
      this._syncingPropertySelection = false
    }
  }

  openLabelsModal(): void {
    if (!this.selectedPropertyViewIds.length) return
    const dialogRef = this._matDialog.open(LabelsModalComponent, {
      width: '50rem',
      data: {
        orgId: this.organization.id,
        type: 'properties',
        viewIds: this.selectedPropertyViewIds,
        goalLabelIds: this.goalLabelIdsForSelection(),
      },
    })
    dialogRef
      .afterClosed()
      .pipe(filter(Boolean), takeUntil(this._unsubscribeAll$))
      .subscribe(() => {
        if (this.currentCycleGoal) this._loadLabels(this.currentCycleGoal)
      })
  }

  goalLabelIdsForSelection(): number[] {
    const goalLabelIds = new Set<number>()
    for (const viewId of this.selectedPropertyViewIds) {
      const viewLabels = [...(this.baselineLabels.get(viewId) ?? []), ...(this.currentLabels.get(viewId) ?? [])]
      for (const label of viewLabels) {
        if (label.goal !== null) goalLabelIds.add(label.statuslabel)
      }
    }
    return [...goalLabelIds]
  }

  openBulkEditGoalNotesModal(): void {
    if (!this.currentGoal || !this.selectedPropertyViewIds.length) return
    const dialogRef = this._matDialog.open(BulkEditGoalNotesModalComponent, {
      width: '40rem',
      data: { goalId: this.currentGoal.id, viewIds: this.selectedPropertyViewIds },
    })
    dialogRef
      .afterClosed()
      .pipe(filter(Boolean), takeUntil(this._unsubscribeAll$))
      .subscribe(() => {
        if (this.currentCycleGoal) this.selectCycleGoal(this.currentCycleGoal)
      })
  }

  onPropertySelectionChanged(event: SelectionChangedEvent): void {
    if (!this.propertyGridApi || this._syncingPropertySelection) return

    if (event.source.startsWith('uiSelectAll')) {
      if (this.propertyGridApi.getSelectedRows().length) {
        this.selectAllProperties()
      } else {
        this.selectNoProperties()
      }
      return
    }

    const currentPageIds = new Set(
      this.goalProperties.map((property) => this._propertyViewId(property)).filter((id): id is number => id !== null),
    )
    const selectedIds = new Set(this.selectedPropertyViewIds.filter((id) => !currentPageIds.has(id)))
    for (const row of this.propertyGridApi
      .getSelectedRows()
      .map((selectedRow: GoalProperty) => this._propertyViewId(selectedRow))
      .filter((id): id is number => id !== null)) {
      selectedIds.add(row)
    }
    this.selectedPropertyViewIds = [...selectedIds]
  }

  onPropertyGridModelUpdated(): void {
    this._syncPropertyGridSelection()
  }

  toggleAccessLevelInstances(): void {
    this.showAccessLevelInstances = !this.showAccessLevelInstances
    const levelCols = this.organization?.access_level_names?.slice(1) ?? []
    if (levelCols.length) {
      this.propertyGridApi?.setColumnsVisible(levelCols, this.showAccessLevelInstances)
    }
  }

  // ─── Actions ───────────────────────────────────────────────────────

  runDataQualityChecks(): void {
    if (!this.organization || !this.currentGoal) return
    const dialogRef = this._matDialog.open(DQCStartModalComponent, {
      width: '40rem',
      data: { orgId: this.organization.id, type: 'properties', viewIds: [], goalId: this.currentGoal.id },
    })
    dialogRef
      .afterClosed()
      .pipe(take(1))
      .subscribe((ran) => {
        if (ran && this.currentCycleGoal) {
          this._reloadPortfolioSummary()
          this._loadProperties(this.propertyPage)
        }
      })
  }

  reviewAndSyncToSalesforce(): void {
    if (!this.currentGoal || !this.currentCycleGoal) return
    this._matDialog.open(SyncSalesforceDialogComponent, {
      autoFocus: false,
      width: '70rem',
      data: {
        goal: this.currentGoal,
        currentCycleGoal: this.currentCycleGoal,
        organization: this.organization,
      } satisfies SyncSalesforceData,
    })
  }

  toggleLabels(key: LabelColumnKey): void {
    this.labelsExpanded[key] = !this.labelsExpanded[key]
    const colId = key === 'baseline' ? 'baseline_labels' : 'current_labels'
    const width = this.labelsExpanded[key] ? 320 : 44
    this.propertyGridApi?.setColumnWidths([{ key: colId, newWidth: width }])
    this.propertyGridApi?.refreshHeader()
    this.propertyGridApi?.refreshCells({ force: true, columns: [colId] })
  }

  // ─── Partner note ─────────────────────────────────────────────────

  setEditingPartnerNote(isEditing: boolean): void {
    if (isEditing) {
      this.partnerNoteForm.enable()
    } else {
      this.partnerNoteForm.disable()
    }
  }

  savePartnerNote(): void {
    if (!this.currentGoal) return
    this._goalService
      .editGoal(this.currentGoal.id, { partner_note: this.partnerNoteForm.value.text }, this.organization.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((goal) => {
        if (this.currentGoal) this.currentGoal = { ...this.currentGoal, partner_note: goal.partner_note }
        this.setEditingPartnerNote(false)
      })
  }

  changePartnerNoteApproval(isApproved: boolean): void {
    if (!this.currentGoal) return
    const now = isApproved ? new Date().toJSON() : null
    const orgUserId$ = isApproved
      ? this._userService.currentUser$.pipe(
          take(1),
          map((u) => u.org_user_id),
        )
      : of(null as number | null)
    orgUserId$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((orgUserId) => {
      this._goalService
        .editGoal(
          this.currentGoal.id,
          {
            partner_note_approval: isApproved,
            partner_note_approval_time: now,
            partner_note_approval_user: orgUserId,
          },
          this.organization.id,
        )
        .pipe(takeUntil(this._unsubscribeAll$))
        .subscribe((goal) => {
          this.currentGoal = goal
        })
    })
  }

  get partnerNoteApprovalLabel(): string {
    if (!this.currentGoal?.partner_note_approval_time) return ''
    const timestamp = new Date(this.currentGoal.partner_note_approval_time).toLocaleString()
    const user = this.currentGoal.partner_note_approval_user_name ?? this.currentGoal.partner_note_approval_user ?? null
    return user ? `Approved on ${timestamp} by ${user}` : `Approved on ${timestamp}`
  }

  // ─── Salesforce ───────────────────────────────────────────────────

  toSettings(): void {
    void this._router.navigate(['/organizations/settings/salesforce-building-integration'])
  }

  loginToSalesforce(): void {
    this._salesforcePortfolioService
      .getLoginUrl(this.organization.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((response) => {
        window.location.href = response.url
      })
  }

  // ─── Export ────────────────────────────────────────────────────────

  scrollToChart(): void {
    this.canvas?.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  exportChart(): void {
    if (!this.canvas) return
    const url = this.canvas.nativeElement.toDataURL('image/png')
    const a = document.createElement('a')
    a.href = url
    a.download = 'portfolio_summary_chart.png'
    a.click()
  }

  exportTable(): void {
    if (!this.goalSummaryData.length) return
    const headers = ['Cycle Name', 'Baseline?', 'EUI', 'Goal', 'Annual % Imp', 'Cumulative % Imp']
    const rows = this.goalSummaryData.map((row) => [
      row['Cycle Name'],
      row['Baseline?'],
      row.EUI,
      row.Goal,
      row['Annual % Imp'],
      row['Cumulative % Imp'],
    ])
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'portfolio_summary_table.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  // ─── Private ─────────────────────────────────────────────────────────

  private _loadProperties(page: number): void {
    if (!this.currentGoal || !this.currentCycleGoal) return
    this._goalService
      .getProperties(this.currentGoal.id, this.currentCycleGoal.id, this.organization.id, page)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((res) => {
        this.goalProperties = res.properties
        this.propertiesPagination = res.pagination
        this.propertyPage = res.pagination.page
        if (!this.propertyColumnDefs.length) this._buildPropertyColumnDefs()
      })
  }

  private _propertyViewId(property: GoalProperty): number | null {
    return property.baseline_view_id ?? property.current_view_id
  }

  private _syncPropertyGridSelection(): void {
    if (!this.propertyGridApi) return
    const selectedIds = new Set(this.selectedPropertyViewIds)
    this._syncingPropertySelection = true
    try {
      this.propertyGridApi.forEachNode((node) => {
        const row = node.data as GoalProperty
        const viewId = this._propertyViewId(row)
        node.setSelected(viewId !== null && selectedIds.has(viewId))
      })
    } finally {
      this._syncingPropertySelection = false
    }
  }

  private _reloadPortfolioSummary(): void {
    if (!this.currentGoal || !this.currentCycleGoal) return
    this._goalService
      .getPortfolioSummary(this.currentGoal.id, this.currentCycleGoal.id, this.organization.id)
      .pipe(take(1))
      .subscribe((portfolioSummary) => {
        this.cycleGoalSummaryData = [portfolioSummary]
        this.portfolioSummary = portfolioSummary
      })
  }

  private _loadLabels(cycleGoal: CycleGoal): void {
    if (!this.currentGoal) return
    const orgId = this.organization.id
    const goalId = this.currentGoal.id
    const baselineCycleId = this.currentGoal.baseline_cycle
    const currentCycleId = cycleGoal.current_cycle.id

    if (baselineCycleId) {
      this._labelService
        .listByCycleGoal(orgId, goalId, baselineCycleId)
        .pipe(take(1))
        .subscribe((labels) => {
          this.baselineLabels = new Map<number, PropertyViewLabel[]>()
          for (const label of labels.filter((item) => item.goal === goalId)) {
            const arr = this.baselineLabels.get(label.propertyview) ?? []
            arr.push(label)
            this.baselineLabels.set(label.propertyview, arr)
          }
          this.propertyGridApi?.refreshCells({ force: true, columns: ['baseline_labels'] })
        })
    }

    this._labelService
      .listByCycleGoal(orgId, goalId, currentCycleId)
      .pipe(take(1))
      .subscribe((labels) => {
        this.currentLabels = new Map<number, PropertyViewLabel[]>()
        for (const label of labels.filter((item) => item.goal === goalId)) {
          const arr = this.currentLabels.get(label.propertyview) ?? []
          arr.push(label)
          this.currentLabels.set(label.propertyview, arr)
        }
        this.propertyGridApi?.refreshCells({ force: true, columns: ['current_labels'] })
      })
  }

  private _applyGoalSelection(goalId: number): void {
    this.selectNoProperties()
    this.currentGoal = this.goals.find((g) => g.id === goalId) ?? null
    if (!this.currentGoal) return

    this._userSettings = {
      ...this._userSettings,
      insights: { ...(this._userSettings.insights ?? {}), portfolioSummary: { goalId } },
    }
    if (this._orgUserId && this.organization?.id) {
      this._organizationService.updateOrganizationUser(this._orgUserId, this.organization.id, this._userSettings).pipe(take(1)).subscribe()
    }

    this.partnerNoteForm.setValue({ text: this.currentGoal.partner_note ?? '' })
    this.currentCycleGoal = null
    this.cycleGoalSummaryData = []
    this.portfolioSummary = null
    this.goalProperties = []
    this.propertiesPagination = null

    this._goalService
      .getWeightedEUIs(this.currentGoal.id, this.organization.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(({ results }) => {
        this._createChart(results)
        this.goalSummaryData = results
      })

    this._goalService
      .getCycleGoals(this.currentGoal.id, this.organization.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((cycleGoals) => {
        if (this.currentGoal) this.currentGoal = { ...this.currentGoal, cycle_goals: cycleGoals }
        // Auto-select the cycle with the latest end date
        const latest = [...cycleGoals].sort((a, b) => new Date(b.current_cycle.end).getTime() - new Date(a.current_cycle.end).getTime())[0]
        if (latest) this.selectCycleGoal(latest)
      })
  }

  private _renderLabelCell(labelsMap: Map<number, PropertyViewLabel[]>, viewId: number | null, expanded: boolean): string {
    if (!viewId) return ''
    const labels = labelsMap.get(viewId) ?? []
    if (!labels.length) return ''
    if (expanded) {
      return labels
        .map((lbl) => {
          const colorClass = lbl.color === 'light blue' ? 'blue light' : lbl.color
          return `<span class="label ${colorClass}">${lbl.name}</span>`
        })
        .join('')
    }
    const segments = labels
      .slice(0, 4)
      .map((lbl) => {
        const bg = LABEL_COLOR_MAP[lbl.color] ?? LABEL_COLOR_MAP.gray
        return `<span style="flex:1;min-width:0;background-color:${bg};" title="${lbl.name}"></span>`
      })
      .join('')
    return `<div style="height:100%;display:flex;align-items:center;"><div style="display:flex;width:36px;height:14px;border-radius:3px;overflow:hidden;">${segments}</div></div>`
  }

  private _buildPropertyColumnDefs(): void {
    const cols = this._propertyColumns
    const findField = (name: string): string => {
      const col = cols.find((c) => c.column_name === name)
      return col ? `${col.column_name}_${col.id}` : name
    }

    // Style helpers
    const yellHdr = { backgroundColor: 'rgba(234,179,8,0.35)' }
    const yellCell = { backgroundColor: 'rgba(234,179,8,0.15)' }
    const redHdr = { backgroundColor: 'rgba(239,68,68,0.35)' }
    const redCell = { backgroundColor: 'rgba(239,68,68,0.15)' }
    const greyHdr = { backgroundColor: 'rgba(107,114,128,0.25)' }
    const greyCell = { backgroundColor: 'rgba(107,114,128,0.10)' }
    const lgHdr = { backgroundColor: 'rgba(107,114,128,0.15)' }
    const lgCell = { backgroundColor: 'rgba(107,114,128,0.08)' }

    // Getter helpers for nested goal_note / historical_note
    const gnGetter = (noteField: keyof GoalNote) => (params: { data: GoalProperty }) => {
      return params.data?.goal_note?.[noteField] ?? null
    }
    const hnGetter = (params: { data: GoalProperty }) => params.data?.historical_note?.text ?? null

    // Matching-criteria columns (excludes property_name which is shown separately)
    const matchingCols: ColDef[] = cols
      .filter((c) => c.is_matching_criteria && c.table_name === 'PropertyState' && c.column_name !== 'property_name')
      .map((c) => ({
        headerName: c.display_name,
        field: `${c.column_name}_${c.id}`,
        filter: 'agTextColumnFilter',
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      }))

    this.propertyColumnDefs = [
      // Access level instance columns — hidden by default, toggled via Show Access Levels
      ...(this.organization?.access_level_names?.slice(1) ?? []).map((level) => ({
        headerName: level,
        field: level,
        colId: level,
        hide: true,
        pinned: 'left' as const,
        lockPinned: true,
        filter: false,
        sortable: true,
        width: 120,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      })),
      // Detail link — always leftmost; user-pinned columns land to its right
      {
        headerName: '',
        field: 'baseline_view_id',
        width: 44,
        maxWidth: 44,
        pinned: 'left',
        lockPosition: 'left',
        lockPinned: true,
        sortable: false,
        filter: false,
        suppressMovable: true,
        cellRenderer: ({ value }: { value: number }) =>
          value
            ? '<div class="flex mt-2 align-center"><span class="material-icons-outlined cursor-pointer" title="Go to property detail" data-action="detail">info</span></div>'
            : '',
      },
      // Matching criteria (pm_property_id, custom_id_1, ubid, etc.)
      ...matchingCols,
      // Standard property info
      {
        headerName: 'Property Name',
        field: findField('property_name'),
        filter: 'agTextColumnFilter',
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Property Type',
        field: findField('property_type'),
        filter: 'agTextColumnFilter',
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Year Built',
        field: findField('year_built'),
        filter: 'agNumberColumnFilter',
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      // Baseline columns (yellow)
      {
        headerName: 'Baseline Area',
        field: 'baseline_sqft',
        filter: 'agNumberColumnFilter',
        headerStyle: yellHdr,
        cellStyle: yellCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Baseline EUI',
        field: 'baseline_eui',
        filter: 'agNumberColumnFilter',
        headerStyle: yellHdr,
        cellStyle: yellCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Baseline kBTU',
        field: 'baseline_kbtu',
        filter: 'agNumberColumnFilter',
        headerStyle: yellHdr,
        cellStyle: yellCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Baseline Labels',
        colId: 'baseline_labels',
        field: 'baseline_view_id',
        width: 44,
        sortable: false,
        filter: false,
        headerStyle: yellHdr,
        cellStyle: { ...yellCell, paddingLeft: '0', paddingRight: '0' },
        headerComponent: PortfolioSummaryLabelHeaderComponent,
        cellRenderer: (params: { data: GoalProperty }) =>
          this._renderLabelCell(this.baselineLabels, params.data?.baseline_view_id ?? null, this.labelsExpanded.baseline),
      },
      // Current cycle columns (red)
      {
        headerName: 'Current Area',
        field: 'current_sqft',
        filter: 'agNumberColumnFilter',
        headerStyle: redHdr,
        cellStyle: redCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Current EUI',
        field: 'current_eui',
        filter: 'agNumberColumnFilter',
        headerStyle: redHdr,
        cellStyle: redCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Current kBTU',
        field: 'current_kbtu',
        filter: 'agNumberColumnFilter',
        headerStyle: redHdr,
        cellStyle: redCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'Current Labels',
        colId: 'current_labels',
        field: 'current_view_id',
        width: 44,
        sortable: false,
        filter: false,
        headerStyle: redHdr,
        cellStyle: { ...redCell, paddingLeft: '0', paddingRight: '0' },
        headerComponent: PortfolioSummaryLabelHeaderComponent,
        cellRenderer: (params: { data: GoalProperty }) =>
          this._renderLabelCell(this.currentLabels, params.data?.current_view_id ?? null, this.labelsExpanded.current),
      },
      // Diff / comparison columns (grey)
      {
        headerName: 'Sq Ft % Change',
        field: 'sqft_change',
        sortable: false,
        filter: false,
        headerStyle: greyHdr,
        cellStyle: greyCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
      },
      {
        headerName: 'EUI % Improvement',
        field: 'eui_change',
        sortable: false,
        filter: false,
        headerStyle: greyHdr,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
        cellStyle: (params) => {
          const value = params.value as number | null
          if (value === null || value === undefined) return greyCell
          return value >= (this.currentGoal?.target_percentage ?? 0)
            ? { backgroundColor: 'rgba(34,197,94,0.30)' }
            : { backgroundColor: 'rgba(239,68,68,0.30)' }
        },
      },
      {
        headerName: 'Question',
        colId: 'goal_note_question',
        sortable: false,
        filter: false,
        width: 300,
        headerStyle: greyHdr,
        cellStyle: greyCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: { values: QUESTION_OPTIONS },
        valueGetter: gnGetter('question'),
        valueSetter: (params) => {
          const row = params.data as GoalProperty
          if (!row.goal_note) return false
          row.goal_note.question = (params.newValue as string) || null
          return true
        },
      },
      {
        headerName: 'Resolution',
        colId: 'goal_note_resolution',
        sortable: false,
        filter: false,
        headerStyle: greyHdr,
        cellStyle: greyCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
        editable: true,
        cellEditor: 'agLargeTextCellEditor',
        valueGetter: gnGetter('resolution'),
        valueSetter: (params) => {
          const row = params.data as GoalProperty
          if (!row.goal_note) return false
          row.goal_note.resolution = (params.newValue as string) || null
          return true
        },
      },
      {
        headerName: 'Historical Notes',
        colId: 'historical_note_text',
        sortable: false,
        filter: false,
        headerStyle: greyHdr,
        cellStyle: greyCell,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
        editable: true,
        cellEditor: 'agLargeTextCellEditor',
        valueGetter: hnGetter,
        valueSetter: (params) => {
          const row = params.data as GoalProperty
          if (!row.historical_note) return false
          row.historical_note.text = (params.newValue as string) ?? ''
          return true
        },
      },
      // Passed Checks — green when true, yellow when false
      {
        headerName: 'Passed Checks',
        colId: 'goal_note_passed_checks',
        sortable: false,
        filter: false,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: { values: [true, false] },
        valueGetter: gnGetter('passed_checks'),
        valueSetter: (params) => {
          const row = params.data as GoalProperty
          if (!row.goal_note) return false
          row.goal_note.passed_checks = params.newValue as boolean
          return true
        },
        cellStyle: (params) => {
          const v = params.value as boolean | null
          if (v === null || v === undefined) return null
          return v ? { backgroundColor: 'rgba(34,197,94,0.30)' } : { backgroundColor: 'rgba(234,179,8,0.30)' }
        },
      },
      // New or Acquired (light grey)
      {
        headerName: 'New or Acquired',
        colId: 'goal_note_new_or_acquired',
        sortable: false,
        filter: false,
        headerStyle: lgHdr,
        headerComponent: PortfolioSummaryHeaderMenuComponent,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: { values: [true, false] },
        valueGetter: gnGetter('new_or_acquired'),
        valueSetter: (params) => {
          const row = params.data as GoalProperty
          if (!row.goal_note) return false
          row.goal_note.new_or_acquired = params.newValue as boolean
          return true
        },
        cellStyle: lgCell,
      },
    ]
  }

  private _createChart(weightedEUIs: WeightedEUI[]): void {
    this.chart?.destroy()
    if (!this.canvas) return
    const ctx = this.canvas.nativeElement.getContext('2d')
    if (!ctx) return
    const goalValue = weightedEUIs[0]?.Goal ?? 0
    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        datasets: [
          {
            data: weightedEUIs.map((we) => we.EUI),
            backgroundColor: ['#1E428A', ...new Array<string>(weightedEUIs.length).fill('#06732cff')],
          },
        ],
        labels: weightedEUIs.map((we) => {
          const match = /\b(\d{4})\b/.exec(we['Cycle Name'])
          return match ? match[1] : we['Cycle Name']
        }),
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: 'Energy Use Intensity by Reporting Period',
            font: { size: 14 },
          },
          annotation: {
            annotations: {
              goalLine: {
                type: 'line',
                yMin: goalValue,
                yMax: goalValue,
                borderColor: 'rgba(128,128,128,0.7)',
                borderWidth: 2,
                borderDash: [6, 4],
                label: {
                  display: true,
                  content: 'GOAL',
                  color: '#1E3A5F',
                  position: 'end',
                  backgroundColor: 'transparent',
                  font: { weight: 'bold' },
                  yAdjust: -14,
                },
              },
            },
          },
        },
        scales: {
          y: {
            title: {
              display: true,
              text: 'EUI (kBtu/sq.ft.)',
            },
          },
          x: {
            title: {
              display: true,
              text: 'Reporting Period',
            },
          },
        },
      },
    })
  }
}
