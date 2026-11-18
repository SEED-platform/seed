import { CommonModule } from '@angular/common'
import type { ElementRef, OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, Router, RouterLink } from '@angular/router'
import type { Chart } from 'chart.js'
import { combineLatest, finalize, skip, Subject, take, takeUntil, tap } from 'rxjs'
import type { Column, CustomReport, CustomReportEvaluateResponse, Cycle, FilterGroup, SimpleCartesianScale, UserAuth } from '@seed/api'
import { ColumnService, CustomReportService, CycleService, FilterGroupService, UserService } from '@seed/api'
import { DeleteModalComponent, PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'

type Aggregation = { id: number; name: string }
type AxisLocation = 'first_axis' | 'second_axis'

const VALID_DATA_TYPES = ['number', 'float', 'integer', 'area', 'eui', 'ghg', 'ghg_intensity']

const COLORS = [
  '#4477AA',
  '#DDDD77',
  '#77CCCC',
  '#117744',
  '#DD7788',
  '#AA4455',
  '#77AADD',
  '#44AAAA',
  '#AAAA44',
  '#114477',
  '#117777',
  '#771122',
  '#777711',
  '#AA7744',
  '#DDAA77',
  '#771155',
  '#AA4488',
  '#CC99BB',
  '#44AA77',
  '#88CCAA',
  '#774411',
]

@Component({
  selector: 'seed-custom-reports',
  templateUrl: './custom-reports.component.html',
  styleUrl: './custom-reports.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, FormsModule, MaterialImports, PageComponent, RouterLink],
})
export class CustomReportsComponent implements OnDestroy, OnInit {
  @ViewChild('chartCanvas', { static: false }) canvas!: ElementRef<HTMLCanvasElement>

  private _columnService = inject(ColumnService)
  private _configService = inject(ConfigService)
  private _customReportService = inject(CustomReportService)
  private _cycleService = inject(CycleService)
  private _dialog = inject(MatDialog)
  private _filterGroupService = inject(FilterGroupService)
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _userService = inject(UserService)
  private _unsubscribeAll$ = new Subject<void>()
  private _currentScheme = 'light'

  readonly aggregations: Aggregation[] = [
    { id: 1, name: 'Average' },
    { id: 2, name: 'Minimum' },
    { id: 3, name: 'Maximum' },
    { id: 4, name: 'Sum' },
    { id: 5, name: 'Count' },
  ]

  // State
  auth: UserAuth = {}
  loading = true
  editing = false
  showConfig = true
  createErrors: string[] = []
  private _initializing = false

  // Data
  customReports: CustomReport[] = []
  selectedReport: CustomReport | null = null
  cycles: Cycle[] = []
  filterGroups: FilterGroup[] = []
  propertyColumns: Column[] = []
  taxLotColumns: Column[] = []
  columnsById: Record<number, Column> = {}
  orgId: number

  // Selection state
  fields = {
    name: '',
    filterGroupCheckboxes: {} as Record<number, boolean>,
    cycleCheckboxes: {} as Record<number, boolean>,
  }
  sourceColumnByLocation: Record<AxisLocation, Column | null> = { first_axis: null, second_axis: null }
  firstAxisAggregations: number[] = []
  secondAxisAggregations: number[] = []

  // View-mode toggles
  selectedCycles: Record<string, Cycle> = {}
  selectedFilterGroups: Record<string, FilterGroup> = {}
  usedCycles: Record<string, Cycle> = {}
  usedFilterGroups: Record<string, FilterGroup> = {}

  // Chart & table
  chart: Chart | null = null
  evaluateData: CustomReportEvaluateResponse['data'] | null = null
  colorsByLabelPrefix: Record<string, string> = {}

  // Table
  selectedTableLocation: AxisLocation = 'first_axis'
  selectedTableAggregation = 1
  showPropertiesForFilterGroup: Record<number, boolean> = {}

  get selectedCyclesCount(): number {
    return Object.keys(this.selectedCycles).length
  }

  get selectedCyclesList(): Cycle[] {
    return Object.values(this.selectedCycles)
  }

  get selectedFilterGroupsList(): FilterGroup[] {
    return Object.values(this.selectedFilterGroups)
  }

  get hasFilterGroups(): boolean {
    return this.selectedReport != null && this.selectedReport.filter_groups.length > 0
  }

  get filteredPropertyColumns(): Column[] {
    const excludeId = this.sourceColumnByLocation.second_axis?.id
    return this.propertyColumns.filter((c) => c.id !== excludeId)
  }

  get filteredPropertyColumnsSecond(): Column[] {
    const excludeId = this.sourceColumnByLocation.first_axis?.id
    return this.propertyColumns.filter((c) => c.id !== excludeId)
  }

  get filteredTaxLotColumns(): Column[] {
    const excludeId = this.sourceColumnByLocation.second_axis?.id
    return this.taxLotColumns.filter((c) => c.id !== excludeId)
  }

  get filteredTaxLotColumnsSecond(): Column[] {
    const excludeId = this.sourceColumnByLocation.first_axis?.id
    return this.taxLotColumns.filter((c) => c.id !== excludeId)
  }

  get firstAxisColumnId(): number | null {
    return this.sourceColumnByLocation.first_axis?.id ?? null
  }

  set firstAxisColumnId(value: number | null) {
    this.selectSourceColumn('first_axis', value)
  }

  get secondAxisColumnId(): number | null {
    return this.sourceColumnByLocation.second_axis?.id ?? null
  }

  set secondAxisColumnId(value: number | null) {
    this.selectSourceColumn('second_axis', value)
  }

  get selectedAggregationName(): string {
    return this.aggregations.find((a) => a.id === this.selectedTableAggregation)?.name ?? ''
  }

  get activeTableColumnId(): number | null {
    return this.sourceColumnByLocation[this.selectedTableLocation]?.id ?? null
  }

  // --- Lifecycle ---

  ngOnInit(): void {
    this._configService.scheme$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((scheme) => {
      this._currentScheme = scheme
      this._applyScheme()
    })

    combineLatest([
      this._userService.auth$,
      this._customReportService.customReports$,
      this._cycleService.cycles$,
      this._filterGroupService.filterGroups$,
      this._columnService.propertyColumns$,
      this._columnService.taxLotColumns$,
      this._userService.currentOrganizationId$,
    ])
      .pipe(
        take(1),
        tap(([auth, reports, cycles, filterGroups, propertyCols, taxLotCols, orgId]) => {
          this.auth = auth
          this.orgId = orgId
          this.customReports = reports
          this.cycles = cycles
          this.filterGroups = filterGroups
          this.propertyColumns = propertyCols.filter((c) => VALID_DATA_TYPES.includes(c.data_type))
          this.taxLotColumns = taxLotCols.filter((c) => VALID_DATA_TYPES.includes(c.data_type))
          this.columnsById = Object.fromEntries([...propertyCols, ...taxLotCols].map((c) => [c.id, c]))
          this._buildColorMap()
          this._initFields()
          this._initializing = true
          this._initData()
          this._initializing = false
          this._loadData()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this._route.paramMap
      .pipe(
        skip(1),
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.editing = false
          this._initFields()
          this._initializing = true
          this._initData()
          this._initializing = false
          this._loadData()
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this.chart?.destroy()
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  // --- Public methods (used by template) ---

  clickNewReport(): void {
    this.selectedReport = {
      id: 0,
      name: 'New Custom Report',
      organization_id: this.orgId,
      filter_groups: [],
      cycles: [],
      parameters: [],
    }
    this.firstAxisAggregations = []
    this.secondAxisAggregations = []
    this.editing = true
    this.fields.name = this.selectedReport.name
  }

  clickEdit(): void {
    if (!this.selectedReport) return
    this.fields.name = this.selectedReport.name
    for (const cycleId of Object.keys(this.fields.cycleCheckboxes)) {
      this.fields.cycleCheckboxes[Number(cycleId)] = false
    }
    for (const filterGroupId of Object.keys(this.fields.filterGroupCheckboxes)) {
      this.fields.filterGroupCheckboxes[Number(filterGroupId)] = false
    }
    for (const cycleId of this.selectedReport.cycles) {
      this.fields.cycleCheckboxes[cycleId] = true
    }
    for (const fgId of this.selectedReport.filter_groups) {
      this.fields.filterGroupCheckboxes[fgId] = true
    }
    this.editing = true
  }

  clickCancel(): void {
    this.selectedReport = null
    this.createErrors = []
    this._initFields()
    this._initializing = true
    this._initData()
    this._initializing = false
    this.editing = false
  }

  clickSave(): void {
    this.createErrors = []

    if (!this.fields.name) {
      this.createErrors.push('A name is required.')
    }

    const checkedFilterGroups = Object.entries(this.fields.filterGroupCheckboxes)
      .filter(([, v]) => v)
      .map(([k]) => Number(k))

    const checkedCycles = Object.entries(this.fields.cycleCheckboxes)
      .filter(([, v]) => v)
      .map(([k]) => Number(k))
    if (checkedCycles.length < 1) {
      this.createErrors.push('At least one cycle must be selected.')
    }

    if (!this.sourceColumnByLocation.first_axis) {
      this.createErrors.push('The first axis must have a source column.')
    }
    if (this.firstAxisAggregations.length < 1) {
      this.createErrors.push('The first axis needs at least one selected aggregation.')
    }
    if (this.sourceColumnByLocation.second_axis && this.secondAxisAggregations.length < 1) {
      this.createErrors.push('The second axis needs at least one selected aggregation.')
    }

    if (this.createErrors.length > 0) {
      return
    }

    const parameters = []
    if (this.sourceColumnByLocation.first_axis) {
      parameters.push({
        column: this.sourceColumnByLocation.first_axis.id,
        location: 'first_axis' as const,
        aggregations: [...this.firstAxisAggregations],
      })
    }
    if (this.sourceColumnByLocation.second_axis) {
      parameters.push({
        column: this.sourceColumnByLocation.second_axis.id,
        location: 'second_axis' as const,
        aggregations: [...this.secondAxisAggregations],
      })
    }

    const payload = {
      name: this.fields.name,
      filter_groups: checkedFilterGroups,
      cycles: checkedCycles,
      parameters,
    }

    this.loading = true

    const request$ = this.selectedReport?.id
      ? this._customReportService.update(this.orgId, this.selectedReport.id, payload)
      : this._customReportService.create(this.orgId, payload)

    request$
      .pipe(
        take(1),
        tap(({ data_view }) => {
          if (!this.selectedReport?.id) {
            void this._router.navigate(['/insights/custom-reports', data_view.id])
          } else {
            this.customReports = this.customReports.map((r) => (r.id === data_view.id ? data_view : r))
            this.selectedReport = data_view
            this._initFields()
            this._initializing = true
            this._initData()
            this._initializing = false
            this._loadData()
            this.editing = false
          }
        }),
        finalize(() => {
          this.loading = false
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  clickDelete(report: CustomReport): void {
    if (!report.id) {
      this.clickCancel()
      return
    }

    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '400px',
      data: { instance: report.name, model: 'Custom Report' },
    })

    dialogRef
      .afterClosed()
      .pipe(take(1))
      .subscribe((confirmed) => {
        if (!confirmed) return
        this.loading = true
        this._customReportService
          .delete(this.orgId, report.id)
          .pipe(
            take(1),
            tap(() => {
              this.customReports = this.customReports.filter((r) => r.id !== report.id)
              if (this.selectedReport?.id === report.id) {
                void this._router.navigate(['/insights/custom-reports'])
              }
            }),
            finalize(() => {
              this.loading = false
            }),
            takeUntil(this._unsubscribeAll$),
          )
          .subscribe()
      })
  }

  toggleFilterGroup(filterGroupId: number): void {
    const fg = this.filterGroups.find((f) => f.id === filterGroupId)
    if (!fg) return
    if (fg.name in this.selectedFilterGroups) {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete this.selectedFilterGroups[fg.name]
      this.selectedFilterGroups = { ...this.selectedFilterGroups }
    } else {
      this.selectedFilterGroups = { ...this.selectedFilterGroups, [fg.name]: fg }
    }
    this._assignDatasets()
  }

  toggleCycle(cycleStart: string): void {
    if (cycleStart in this.selectedCycles) {
      const { [cycleStart]: _, ...rest } = this.selectedCycles
      this.selectedCycles = rest
    } else if (this.usedCycles[cycleStart]) {
      this.selectedCycles = { ...this.selectedCycles, [cycleStart]: this.usedCycles[cycleStart] }
    }
    this._assignDatasets()
  }

  toggleAggregation(location: AxisLocation, aggregationId: number): void {
    if (!this.sourceColumnByLocation[location]) return
    const aggregations = location === 'first_axis' ? this.firstAxisAggregations : this.secondAxisAggregations
    const idx = aggregations.indexOf(aggregationId)
    if (idx > -1) {
      aggregations.splice(idx, 1)
    } else {
      aggregations.push(aggregationId)
    }
    if (this.chart) {
      if (!this.editing && !this._initializing) {
        this.clickEdit()
      }
      this._assignDatasets()
    }
  }

  hasAggregation(location: AxisLocation, aggregationId: number): boolean {
    const aggregations = location === 'first_axis' ? this.firstAxisAggregations : this.secondAxisAggregations
    return aggregations.includes(aggregationId)
  }

  selectSourceColumn(location: AxisLocation, columnId: number | null, reloadData = true): void {
    this.sourceColumnByLocation[location] = columnId ? (this.columnsById[columnId] ?? null) : null
    if (this.editing && !reloadData) return

    if (location === 'first_axis') {
      this.firstAxisAggregations = []
    } else {
      this.secondAxisAggregations = []
    }

    if (reloadData && this.selectedReport?.id) {
      this._loadData()
      if (!this.editing && !this._initializing) {
        this.clickEdit()
      }
    }
    this._assignDatasets()
  }

  isFilterGroupSelected(name: string): boolean {
    return name in this.selectedFilterGroups
  }

  isCycleSelected(start: string): boolean {
    return start in this.selectedCycles
  }

  downloadChart(): void {
    if (!this.chart) return
    const a = document.createElement('a')
    a.href = this.chart.toBase64Image()
    a.download = 'Custom Report.png'
    a.click()
  }

  getTableValue(columnId: number, filterGroupId: number, cycleId: number, aggregationName: string): number | null {
    const cycleData = this.evaluateData?.columns_by_id?.[columnId]?.filter_groups_by_id?.[filterGroupId]?.cycles_by_id?.[cycleId]
    if (!cycleData) return null
    return (cycleData as unknown as Record<string, number | null>)[aggregationName] ?? null
  }

  getPropertyValue(columnId: number, filterGroupId: number, cycleId: number, viewName: string): number | null {
    return (
      this.evaluateData?.columns_by_id?.[columnId]?.filter_groups_by_id?.[filterGroupId]?.cycles_by_id?.[cycleId]?.views_by_default_field?.[
        viewName
      ] ?? null
    )
  }

  getPropertiesForFilterGroup(filterGroupId: number): [string, string][] {
    const views = this.evaluateData?.views_by_filter_group_id?.[filterGroupId]
    if (!views) return []
    return Object.entries(views)
  }

  getTableValueNoFilterGroup(columnId: number, cycleId: number, aggregationName: string): number | null {
    const filterGroupsById = this.evaluateData?.columns_by_id?.[columnId]?.filter_groups_by_id
    if (!filterGroupsById) return null
    const firstKey = Object.keys(filterGroupsById)[0]
    if (firstKey == null) return null
    const cycleData = filterGroupsById[Number(firstKey)]?.cycles_by_id?.[cycleId]
    if (!cycleData) return null
    return (cycleData as unknown as Record<string, number | null>)[aggregationName] ?? null
  }

  togglePropertyExpansion(filterGroupId: number): void {
    this.showPropertiesForFilterGroup[filterGroupId] = !this.showPropertiesForFilterGroup[filterGroupId]
  }

  // --- Private methods ---

  private _buildColorMap(): void {
    let colorIndex = 0
    const filterGroupNames = this.filterGroups.length > 0 ? this.filterGroups.map((fg) => fg.name) : ['All']
    for (const agg of this.aggregations) {
      for (const fgName of filterGroupNames) {
        this.colorsByLabelPrefix[`${fgName} - ${agg.name}`] = COLORS[colorIndex % COLORS.length]
        colorIndex++
      }
    }
  }

  private _initFields(): void {
    this.fields.filterGroupCheckboxes = {}
    this.fields.cycleCheckboxes = {}
    for (const fg of this.filterGroups) {
      this.fields.filterGroupCheckboxes[fg.id] = false
    }
    for (const c of this.cycles) {
      this.fields.cycleCheckboxes[c.id] = false
    }
    this.sourceColumnByLocation = { first_axis: null, second_axis: null }
    this.firstAxisAggregations = []
    this.secondAxisAggregations = []
  }

  private _initData(): void {
    const routeId = Number(this._route.snapshot.paramMap.get('id'))
    this.selectedReport = routeId ? (this.customReports.find((r) => r.id === routeId) ?? null) : null

    if (this.selectedReport) {
      this.firstAxisAggregations = []
      this.secondAxisAggregations = []
      this.fields.name = this.selectedReport.name

      // Load cycles
      this.usedCycles = {}
      for (const cycle of this.cycles) {
        if (this.selectedReport.cycles.includes(cycle.id)) {
          this.usedCycles[cycle.start] = cycle
        }
      }
      this.selectedCycles = { ...this.usedCycles }

      // Load filter groups
      this.usedFilterGroups = {}
      for (const fg of this.filterGroups) {
        if (this.selectedReport.filter_groups.includes(fg.id)) {
          this.usedFilterGroups[fg.name] = fg
          this.showPropertiesForFilterGroup[fg.id] = false
        }
      }
      this.selectedFilterGroups = { ...this.usedFilterGroups }

      // Load axes
      const firstParam = this.selectedReport.parameters.find((p) => p.location === 'first_axis')
      if (firstParam) {
        this.selectedTableLocation = 'first_axis'
        this.selectedTableAggregation = firstParam.aggregations[0] ?? 1
        this.selectSourceColumn('first_axis', firstParam.column, false)
        for (const aggId of firstParam.aggregations) {
          this.toggleAggregation('first_axis', aggId)
        }
      }
      const secondParam = this.selectedReport.parameters.find((p) => p.location === 'second_axis')
      if (secondParam) {
        this.selectSourceColumn('second_axis', secondParam.column, false)
        for (const aggId of secondParam.aggregations) {
          this.toggleAggregation('second_axis', aggId)
        }
      }
    } else {
      this.usedCycles = {}
      this.selectedCycles = {}
      this.usedFilterGroups = {}
      this.selectedFilterGroups = {}
    }
  }

  private _loadData(): void {
    if (!this.selectedReport?.id) {
      this.loading = false
      return
    }
    this.loading = true
    const columns = [this.sourceColumnByLocation.first_axis, this.sourceColumnByLocation.second_axis]
      .filter((c): c is Column => c != null)
      .map((c) => c.id)

    this._customReportService
      .evaluate(this.orgId, this.selectedReport.id, columns)
      .pipe(
        take(1),
        tap((data) => {
          this.evaluateData = data
          setTimeout(() => {
            this._buildChart()
          }, 0)
        }),
        finalize(() => {
          this.loading = false
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  private _buildChart(): void {
    if (!this.evaluateData?.graph_data || !this.canvas) {
      return
    }

    this.chart?.destroy()

    const firstAxisName = this.sourceColumnByLocation.first_axis?.display_name ?? 'y1'
    const secondAxisName = this.sourceColumnByLocation.second_axis?.display_name ?? 'y2'

    void import('chart.js').then(({ Chart }) => {
      this.chart = new Chart(this.canvas.nativeElement, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
          plugins: {
            title: { display: true, align: 'start', padding: { top: 10, bottom: 20 } },
            legend: {
              position: 'right',
              maxWidth: 500,
              title: {
                display: true,
                text: 'Solid Line (Left Axis) - Dashed Line (Right Axis)',
              },
              labels: {
                boxHeight: 0,
                boxWidth: 50,
                sort: (a, b) => a.text.localeCompare(b.text),
              },
            },
          },
          scales: {
            y1: {
              beginAtZero: true,
              position: 'left',
              display: false,
              title: { text: firstAxisName, display: true },
            },
            y2: {
              beginAtZero: true,
              position: 'right',
              display: false,
              title: { text: secondAxisName, display: false },
            },
          },
        },
      })

      this._applyScheme()
      this._assignDatasets()
    })
  }

  private _applyScheme(): void {
    if (!this.chart) return
    const gridColor = this._currentScheme === 'light' ? '#0000001a' : '#ffffff2b'
    const scales = this.chart.options.scales ?? {}
    if (scales.y1) scales.y1.grid = { color: gridColor }
    if (scales.y2) scales.y2.grid = { color: gridColor }
    if (scales.x) scales.x.grid = { color: gridColor }
    this.chart.update()
  }

  private _assignDatasets(): void {
    if (!this.evaluateData?.graph_data || !this.chart) return

    const xAxisLabels = this.evaluateData.graph_data.labels
    const selectedCycleNames = Object.values(this.selectedCycles).map((c) => c.name)
    const xAxisLabelsMask = xAxisLabels.map((l) => selectedCycleNames.includes(l))

    const datasets: Record<string, unknown>[] = []
    const noFilterGroups = !this.hasFilterGroups
    const axis1Names = this.firstAxisAggregations.map((id) => this.aggregations.find((a) => a.id === id)?.name ?? '')
    const axis2Names = this.secondAxisAggregations.map((id) => this.aggregations.find((a) => a.id === id)?.name ?? '')

    // Show/hide y1
    const scales = this.chart.options.scales ?? {}
    if (scales.y1) scales.y1.display = axis1Names.length > 0

    // First axis datasets
    const axis1Column = this.sourceColumnByLocation.first_axis?.display_name
    if (axis1Column) {
      for (const aggregation of axis1Names) {
        for (const ds of this.evaluateData.graph_data.datasets) {
          const escapedColumn = this._escapeRegexValue(ds.column)
          const columnPattern = new RegExp(`^${escapedColumn}( \\(.+?\\))?$`)
          if (
            aggregation === ds.aggregation
            && columnPattern.test(axis1Column)
            && (noFilterGroups || ds.filter_group in this.selectedFilterGroups)
          ) {
            const color = this.colorsByLabelPrefix[`${ds.filter_group} - ${ds.aggregation}`]
            datasets.push({
              ...ds,
              label: `${ds.filter_group} - ${ds.aggregation} - ${ds.column}`,
              backgroundColor: color,
              borderColor: color,
              tension: 0.1,
              yAxisID: 'y1',
              data: ds.data.filter((_, i) => xAxisLabelsMask[i]),
            })
          }
        }
      }
    }

    // Second axis datasets
    if (this.sourceColumnByLocation.second_axis) {
      const axis2Column = this.sourceColumnByLocation.second_axis.display_name
      if (scales.y2) {
        ;(scales.y2 as Record<string, unknown>).display = true
        ;(scales.y2 as SimpleCartesianScale).title = { text: axis2Column, display: true }
      }

      for (const aggregation of axis2Names) {
        for (const ds of this.evaluateData.graph_data.datasets) {
          const escapedColumn = this._escapeRegexValue(ds.column)
          const columnPattern = new RegExp(`^${escapedColumn}( \\(.+?\\))?$`)
          if (
            aggregation === ds.aggregation
            && columnPattern.test(axis2Column)
            && (noFilterGroups || ds.filter_group in this.selectedFilterGroups)
          ) {
            const color = this.colorsByLabelPrefix[`${ds.filter_group} - ${ds.aggregation}`]
            datasets.push({
              ...ds,
              label: `${ds.filter_group} - ${ds.aggregation} - ${ds.column}`,
              backgroundColor: color,
              borderColor: color,
              tension: 0.1,
              yAxisID: 'y2',
              borderDash: [10, 15],
              data: ds.data.filter((_, i) => xAxisLabelsMask[i]),
            })
          }
        }
      }
    } else if (scales.y2) {
      ;(scales.y2 as SimpleCartesianScale).title = { display: false, text: '' }
    }

    // Set y-axis max
    const allValues = datasets.flatMap((d) => (d.data as number[]) ?? []).filter((v) => v != null)
    const yMax = allValues.length > 0 ? Math.trunc(1.1 * Math.max(...allValues)) : 100
    if (scales.y1) scales.y1.max = yMax
    if (scales.y2) scales.y2.max = yMax

    this.chart.data.labels = xAxisLabels.filter((_, i) => xAxisLabelsMask[i])
    this.chart.data.datasets = datasets as never[]
    if (this.selectedReport) {
      const titlePlugin = this.chart.options.plugins?.title
      if (titlePlugin) titlePlugin.text = `Selected Configuration: ${this.selectedReport.name}`
    }
    this.chart.update()
  }

  private _escapeRegexValue(value: string): string {
    return value.replace(/[-.*+?^${}()|[\]\\]/g, '\\$&')
  }
}
