import { CommonModule, Location } from '@angular/common'
import type { ElementRef, OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import type { ParamMap } from '@angular/router'
import { ActivatedRoute, Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, RowClickedEvent } from 'ag-grid-community'
import type { ActiveElement, TooltipItem } from 'chart.js'
import { Chart } from 'chart.js'
import type { AnnotationOptions } from 'chartjs-plugin-annotation'
import { combineLatest, debounceTime, EMPTY, filter, map, merge, Subject, switchMap, take, takeUntil, tap, zip } from 'rxjs'
import type {
  AccessLevelInstancesByDepth,
  AccessLevelsByDepth,
  Column,
  CurrentUser,
  Cycle,
  FilterGroup,
  InsightDatasetVisibility,
  Organization,
  Program,
  ProgramData,
  PropertyInsightDataset,
  PropertyInsightPoint,
  PropertyInsightsUserSettings,
  ResultsByCycles,
  SimpleCartesianScale,
} from '@seed/api'
import { ColumnService, CycleService, FilterGroupService, OrganizationService, ProgramService, UserService } from '@seed/api'
import { NotFoundComponent, PageComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { LabelsModalComponent } from 'app/modules/inventory/actions'
import { ProgramConfigComponent } from '../config'

@Component({
  selector: 'seed-property-insights',
  templateUrl: './property-insights.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [
    AgGridAngular,
    CommonModule,
    FormsModule,
    PageComponent,
    MaterialImports,
    NotFoundComponent,
    ProgressBarComponent,
    ReactiveFormsModule,
  ],
})
export class PropertyInsightsComponent implements OnDestroy, OnInit {
  @ViewChild('propertyInsightsChart', { static: true }) canvas!: ElementRef<HTMLCanvasElement>
  private _location = inject(Location)
  private _columnService = inject(ColumnService)
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _filterGroupService = inject(FilterGroupService)
  private _programService = inject(ProgramService)
  private _dialog = inject(MatDialog)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _snackBar = inject(SnackBarService)
  private _userService = inject(UserService)
  private _persistSettings$ = new Subject<void>()
  private _reset$ = new Subject<void>()
  private _unsubscribeAll$ = new Subject<void>()

  accessLevelNames: AccessLevelInstancesByDepth['accessLevelNames'] = []
  accessLevelInstancesByDepth: AccessLevelsByDepth = {}
  accessLevelInstances: AccessLevelsByDepth[keyof AccessLevelsByDepth] = []
  annotations: Record<string, AnnotationOptions>
  chart: Chart
  colDefs: ColDef[] = []
  colors: Record<string, string> = { compliant: '#77CCCB', 'non-compliant': '#A94455', unknown: '#DDDDDD' }
  currentUser: CurrentUser
  cycles: Cycle[]
  data: ProgramData
  datasets: PropertyInsightDataset[] = []
  datasetOrder: InsightDatasetVisibility[] = ['compliant', 'non-compliant', 'unknown', 'whisker']
  datasetVisibility: InsightDatasetVisibility[] = [...this.datasetOrder]
  filterGroups: FilterGroup[] = []
  gridOptions = { rowClass: 'cursor-pointer' }
  gridTheme$ = this._configService.gridTheme$
  loading = true
  metricTypes = [
    { key: 0, value: 'Energy Metric' },
    { key: 1, value: 'Emission Metric' },
  ]
  org: Organization
  programId: number
  program: Program
  programs: Program[]
  propertyColumns: Column[]
  programCycles: Cycle[] = []
  programMetricTypes: { key: number; value: string }[] = []
  programXAxisColumns: Column[] = []
  rankedCol = { display_name: 'Ranked Distance to Compliance', id: 0 } as Column
  results = { y: 0, n: 0, u: 0 }
  rowData: Record<string, PropertyInsightPoint[]> = {}
  scheme: 'dark' | 'light' = 'light'
  xCategorical = false
  xAxisColumns: Column[]
  xAxisDataTypes = ['number', 'string', 'float', 'integer', 'ghg', 'ghg_intensity', 'area', 'eui', 'boolean']

  form = new FormGroup({
    cycleId: new FormControl<number>(null),
    metricType: new FormControl<0 | 1>(0),
    xAxisColumnId: new FormControl<number>(null),
    accessLevel: new FormControl<string | null>(null),
    accessLevelInstanceId: new FormControl<number | null>(null),
    program: new FormControl<Program>(null),
    annotationVisibility: new FormControl(true),
  })

  get cycleId() {
    return this.form.value.cycleId
  }

  get metricType() {
    return this.form.value.metricType
  }

  get xAxisColumnId() {
    return this.form.value.xAxisColumnId
  }

  get accessLevelInstanceId() {
    return this.form.value.accessLevelInstanceId
  }

  ngOnInit() {
    this.watchForm()
    this.getAliTree()

    this._persistSettings$
      .pipe(
        filter(() => !!(this.currentUser && this.org)),
        debounceTime(300),
        switchMap(() =>
          this._organizationService.updateOrganizationUser(this.currentUser.org_user_id, this.org.id, this.currentUser.settings),
        ),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this._route.paramMap.pipe(takeUntil(this._unsubscribeAll$)).subscribe((params: ParamMap) => {
      this.programId = parseInt(params.get('id') ?? '', 10)
      this._reset$.next()
      this.initChart()
      this.setScheme()
      this.initProgram()
    })
  }

  initProgram(): void {
    this.getDependencies()
      .pipe(
        debounceTime(300),
        tap((dependencies) => {
          this.setDependencies(dependencies)
          this.getPrograms()
        }),
        takeUntil(merge(this._unsubscribeAll$, this._reset$)),
      )
      .subscribe()
  }

  getDependencies() {
    return combineLatest({
      org: this._organizationService.currentOrganization$,
      cycles: this._cycleService.cycles$,
      propertyColumns: this._columnService.propertyColumns$,
      filterGroups: this._filterGroupService.filterGroups$,
      currentUser: this._userService.currentUser$,
    })
  }

  setDependencies({
    org,
    cycles,
    propertyColumns,
    filterGroups,
    currentUser,
  }: {
    org: Organization;
    cycles: Cycle[];
    propertyColumns: Column[];
    filterGroups: FilterGroup[];
    currentUser: CurrentUser;
  }) {
    this.org = org
    this.cycles = cycles
    this.currentUser = currentUser
    this.propertyColumns = propertyColumns
    this.filterGroups = filterGroups
    this.xAxisColumns = this.propertyColumns.filter((c) => this.isValidColumn(c, this.xAxisDataTypes))
  }

  getPrograms() {
    this._programService.programs$
      .pipe(
        filter(() => !!this.org),
        tap((programs) => {
          this.programs = programs.filter((p) => p.organization_id === this.org.id).sort((a, b) => naturalSort(a.name, b.name))
          const hasRouteProgramId = Number.isFinite(this.programId)
          const savedProgramId = this.currentUser?.settings?.insights?.propertyInsights?.programId
          this.program = hasRouteProgramId
            ? this.programs.find((p) => p.id === this.programId)
            : this.programs.find((p) => p.id === savedProgramId)
          if (!this.program) {
            this.loading = false
            if (!hasRouteProgramId && this.programs.length) {
              this.programChange(this.programs[0])
            }
          }
        }),
        filter(() => !!this.program),
        switchMap(() => this.evaluateProgram(this.accessLevelInstanceId)),
        tap(() => {
          this.setForm()
        }),
        takeUntil(merge(this._unsubscribeAll$, this._reset$)),
      )
      .subscribe()
  }

  setForm() {
    if (!this.program) return
    this.setFormOptions()
    const savedSettings = this.currentUser?.settings?.insights?.propertyInsights
    const { cycleId: stateCycleId, label: stateDatasetLabel } = this.getNavigationState()

    this.datasetVisibility = this.validDatasetVisibility(savedSettings?.datasetVisibility)
    if (stateDatasetLabel) {
      this.handleLegendVisibility(stateDatasetLabel)
    }

    const savedAccessLevel = savedSettings?.accessLevel
    const validAccessLevel
      = savedAccessLevel && this.accessLevelNames.includes(savedAccessLevel) ? savedAccessLevel : (this.accessLevelNames?.at(-1) ?? null)
    this.getPossibleAccessLevelInstances(validAccessLevel)

    const validAliId
      = this.accessLevelInstances.find((ali) => ali.id === savedSettings?.accessLevelInstanceId)?.id
        ?? this.accessLevelInstances[0]?.id
        ?? null

    const validStateCycleId = stateCycleId && this.program.cycles.includes(stateCycleId) ? stateCycleId : null
    const savedCycleId = savedSettings?.cycleId
    const validSavedCycleId = savedCycleId && this.program.cycles.includes(savedCycleId) ? savedCycleId : null
    const cycleId = validStateCycleId ?? validSavedCycleId ?? this.program.cycles[0]

    const defaultMetricType: 0 | 1 = this.program.actual_energy_column ? 0 : 1
    const validMetricType = this.programMetricTypes.find(({ key }) => key === savedSettings?.metricType)?.key ?? defaultMetricType

    const validXAxisColumnId
      = this.programXAxisColumns.find((column) => column.id === savedSettings?.xAxisColumnId)?.id
        ?? this.program.x_axis_columns[0]
        ?? this.rankedCol.id

    const data: Record<string, unknown> = {
      cycleId,
      xAxisColumnId: validXAxisColumnId,
      metricType: validMetricType,
      accessLevel: validAccessLevel,
      accessLevelInstanceId: validAliId,
    }

    // wait for DOM to update before patching to avoid blank selections
    setTimeout(() => {
      this.form.patchValue(data)
      this.persistPropertyInsightsSettings()
    })
  }

  watchForm() {
    // Developer Note: use map to track which value changes
    merge(
      this.form.get('cycleId')?.valueChanges.pipe(map((value) => ({ field: 'cycleId', value }))),
      this.form.get('xAxisColumnId')?.valueChanges.pipe(map((value) => ({ field: 'xAxisColumnId', value }))),
      this.form.get('metricType')?.valueChanges.pipe(map((value) => ({ field: 'metricType', value }))),
    )
      .pipe(
        tap(() => {
          this.loading = true
        }),
        debounceTime(300),
        tap(() => {
          this.setChart()
          if (this.cycleId) {
            this.setResults()
            this.loading = false
          }
          this.persistPropertyInsightsSettings()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this.form
      .get('accessLevel')
      ?.valueChanges.pipe(
        tap((accessLevel) => {
          this.getPossibleAccessLevelInstances(accessLevel)
          const aliIdCtrl = this.form.get('accessLevelInstanceId')
          if (!aliIdCtrl) return
          const currentAliId = aliIdCtrl.value
          const validAliId = this.accessLevelInstances.some(({ id }) => id === currentAliId)
            ? currentAliId
            : (this.accessLevelInstances[0]?.id ?? null)
          if (validAliId !== currentAliId) {
            aliIdCtrl.setValue(validAliId)
          }
          this.persistPropertyInsightsSettings()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()

    this.form
      .get('accessLevelInstanceId')
      ?.valueChanges.pipe(
        tap(() => {
          this.loading = true
        }),
        filter((id) => !!(id && this.org && this.cycleId)),
        switchMap((id) => this.evaluateProgram(id)),
        tap(() => {
          this.setChart()
          this.setResults()
          this.loading = false
          this.persistPropertyInsightsSettings()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  setChart() {
    this.clearLabels()
    this.setChartSettings()
    this.loadDatasets()
    this.chart.update()
    this.sortLabels()
    this.chart.resetZoom()
  }

  getAliTree() {
    zip(this._organizationService.accessLevelTree$, this._organizationService.accessLevelInstancesByDepth$)
      .pipe(
        tap(([accessLevelTree, accessLevelsByDepth]) => {
          this.accessLevelNames = accessLevelTree.accessLevelNames
          this.accessLevelInstancesByDepth = accessLevelsByDepth
          this.getPossibleAccessLevelInstances(this.accessLevelNames?.at(-1))

          // suggest access level instance if null
          this.form.get('accessLevelInstanceId')?.setValue(this.accessLevelInstances[0]?.id)
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  getPossibleAccessLevelInstances(accessLevelName: string | null | undefined): void {
    if (!accessLevelName) {
      this.accessLevelInstances = []
      return
    }

    const depth = this.accessLevelNames.findIndex((name) => name === accessLevelName)
    this.accessLevelInstances = this.accessLevelInstancesByDepth[depth] ?? []
  }

  programChange(program: Program | number | null | undefined) {
    const programId = typeof program === 'number' ? program : program?.id
    this.form.reset()
    const segments = ['/insights/property-insights']
    if (programId) segments.push(programId.toString())
    void this._router.navigate(segments)
  }

  compareSelection = (a: { id: number }, b: { id: number }) => a?.id === b?.id

  evaluateProgram(aliId: number = null) {
    if (this.program?.organization_id !== this.org.id) {
      this.loading = false
      this.clearChart()
      return EMPTY
    }

    return this._programService.evaluate(this.org.id, this.program.id, aliId).pipe(
      tap((data) => {
        this.data = data
        this.setResults()
      }),
      take(1),
    )
  }

  getNavigationState() {
    // Use incoming state if coming from program overview, then clear to avoid stale re-use.
    const state = this._location.getState() as { cycleId?: number; label?: string }
    history.replaceState({}, document.title)
    return state
  }

  handleLegendVisibility(dataset: string) {
    if (!dataset) {
      this.datasetVisibility = [...this.datasetOrder]
      return
    }

    if (this.datasetOrder.includes(dataset as InsightDatasetVisibility)) {
      this.datasetVisibility = [dataset as InsightDatasetVisibility]
      if (dataset === 'non-compliant') {
        this.datasetVisibility.push('whisker')
      }
    }
  }

  validDatasetVisibility(datasetVisibility: InsightDatasetVisibility[] = []): InsightDatasetVisibility[] {
    if (!datasetVisibility?.length) return [...this.datasetOrder]
    return datasetVisibility.filter((value) => this.datasetOrder.includes(value))
  }

  persistPropertyInsightsSettings() {
    if (!this.currentUser || !this.program || !this.org) return

    this.currentUser.settings.insights ??= {}
    const settings: PropertyInsightsUserSettings = {
      accessLevel: this.form.value.accessLevel,
      accessLevelInstanceId: this.accessLevelInstanceId,
      cycleId: this.cycleId,
      datasetVisibility: this.datasetVisibility,
      metricType: this.metricType,
      programId: this.program.id,
      xAxisColumnId: this.xAxisColumnId,
    }
    this.currentUser.settings.insights.propertyInsights = settings
    this._persistSettings$.next()
  }

  setFormOptions() {
    const { cycles, x_axis_columns, actual_emission_column, actual_energy_column } = this.program
    this.programMetricTypes = []
    if (actual_emission_column) this.programMetricTypes.push({ key: 1, value: 'Emission Metric' })
    if (actual_energy_column) this.programMetricTypes.push({ key: 0, value: 'Energy Metric' })
    this.programCycles = this.cycles.filter((c) => cycles.includes(c.id))
    this.programXAxisColumns = [...this.xAxisColumns.filter((c) => x_axis_columns.includes(c.id)), this.rankedCol]
  }

  validateProgram() {
    const { actual_emission_column, actual_energy_column } = this.program
    if (!this.data) {
      this.clearChart()
      return false
    }
    const validEnergy = this.metricType === 0 && !!actual_energy_column
    const validEmission = this.metricType === 1 && !!actual_emission_column
    return validEnergy || validEmission
  }

  isValidColumn(column: Column, validTypes: string[]) {
    const isAllowedType = validTypes.includes(column.data_type)
    const notRelated = !column.related
    const notDerived = !column.derived_column
    return isAllowedType && notRelated && notDerived
  }

  setResults() {
    if (!this.data || !this.cycleId) return

    const { y, n, u } = this.data.results_by_cycles[this.cycleId] as { y: number[]; n: number[]; u: number[] }
    this.results = { y: y.length, n: n.length, u: u.length }

    const { scales } = this.chart.options as { scales: { x: { title: { text: string } }; y: { title: { text: string } } } }
    this.colDefs = [
      { field: 'x', headerName: `X: ${scales.x.title.text}`, flex: 1 },
      { field: 'y', headerName: `Y: ${scales.y.title.text}`, flex: 1 },
      { field: 'distance', headerName: 'Distance to Target', flex: 1 },
    ]

    this.rowData = this.chart.data.datasets.reduce(
      (acc, { label, data }) => {
        acc[label] = data
        return acc
      },
      { compliant: [], 'non-compliant': [], unknown: [] },
    )
  }

  setScheme() {
    this._configService.scheme$.pipe(takeUntil(merge(this._unsubscribeAll$, this._reset$))).subscribe((scheme) => {
      this.scheme = scheme
      const color = scheme === 'light' ? '#0000001a' : '#ffffff2b'
      this.chart.options.scales.x.grid = { color }
      this.chart.options.scales.y.grid = { color }
      this.chart.update()
    })
  }

  /*
   * Step 2, set chart settings (axes name, background, labels...)
   */
  setChartSettings() {
    if (!this.program) return
    const [xAxisName, yAxisName] = this.getXYAxisName()
    const xScale = this.chart.options.scales.x as SimpleCartesianScale
    xScale.type = this.xCategorical ? 'category' : 'linear'
    xScale.title = { display: true, text: xAxisName }

    const yScale = this.chart.options.scales.y as SimpleCartesianScale
    yScale.title = { display: true, text: yAxisName }
    this.chart.options.plugins.annotation ??= { annotations: {} }
    this.chart.options.plugins.annotation.annotations = this.annotations
    this.chart.options.scales.x.ticks = {
      callback(value) {
        const label = this.getLabelForValue(value as number)
        if (xAxisName?.toLowerCase().includes('year')) {
          return label.replace(',', '')
        }
        return label
      },
    }
  }

  getXYAxisName(): string[] {
    const xAxisCol = this.programXAxisColumns.find((col) => col.id === this.xAxisColumnId)
    if (!xAxisCol || !this.program) return [null, null]

    const xAxisName = xAxisCol.display_name
    this.xCategorical = ['string', 'boolean'].includes(xAxisCol.data_type)
    const energyCol = this.propertyColumns.find((col) => col.id === this.program.actual_energy_column)
    const emissionCol = this.propertyColumns.find((col) => col.id === this.program.actual_emission_column)
    const yAxisName = this.metricType === 0 ? energyCol?.display_name : emissionCol?.display_name

    return [xAxisName, yAxisName]
  }

  setDatasetColor() {
    for (const ds of this.chart.data.datasets) {
      ;(ds as { backgroundColor?: string }).backgroundColor = this.colors[ds.label]
    }
  }

  /*
   * Step 3: Loads datasets into the chart.
   */
  loadDatasets() {
    if (!this.program || !this.data) return

    this.resetDatasets()

    const numProperties = Object.values(this.data.properties_by_cycles).reduce((acc, curr) => acc + curr.length, 0)
    if (numProperties > 3000) {
      this._snackBar.alert('Too many properties to chart. Update program and try again.')
      return
    }

    this.formatDataPoints()
    this.formatNonCompliantPoints()
    this.chart.data.datasets = this.datasets

    this.chart.data.labels = []
    if (this.xCategorical) {
      const labels = this.datasets.flatMap((dataset) => dataset.data.map((point) => point.x)).filter((label) => label !== undefined)
      this.chart.data.labels = [...new Set(labels)]
    }

    const flatData = this.datasets.flatMap((dataset) => dataset.data)
    if (flatData.length) {
      const yMax = Math.max(...flatData.map((p) => p.y))
      const xMax = Math.max(...flatData.map((p) => p.x))
      this.chart.options.scales.y.suggestedMax = yMax * 1.1
      this.chart.options.scales.x.suggestedMax = xMax * 1.1
    }

    this.setDatasetColor()
    this.chart.options.plugins.annotation ??= { annotations: {} }
    this.chart.options.plugins.annotation.annotations = this.annotations
  }

  formatDataPoints() {
    const { metric, results_by_cycles } = this.data

    const properties = this.data.properties_by_cycles[this.cycleId] ?? []
    const cycleResult = results_by_cycles[this.cycleId] as ResultsByCycles

    for (const prop of properties) {
      const id = prop.id as number
      const nonCompliant = cycleResult.n.includes(id)
      const name = this.getValue(prop, 'startsWith', this.org.property_display_field) as string
      const x = this.getValue(prop, 'endsWith', `_${this.xAxisColumnId}`) as number
      let target: number
      let distance: number = null

      const actualCol = this.metricType === 0 ? metric.actual_energy_column : metric.actual_emission_column
      const targetCol = this.metricType === 0 ? metric.target_energy_column : metric.target_emission_column
      const hasTarget = this.metricType === 0 ? !metric.energy_bool : !metric.emission_bool

      const y = this.getValue(prop, 'endsWith', `_${actualCol}`) as number
      if (hasTarget) {
        target = this.getValue(prop, 'endsWith', `_${targetCol}`) as number
        distance = nonCompliant ? Math.abs(target - y) : null
      }

      const item: PropertyInsightPoint = { id, name, x, y, target, distance }

      // place in appropriate dataset
      if (cycleResult.y.includes(id)) {
        this.datasets[0].data.push(item)
      } else if (nonCompliant) {
        this.datasets[1].data.push(item)
      } else {
        this.datasets[2].data.push(item)
      }
    }
  }

  formatNonCompliantPoints() {
    this.annotations = {}
    const program = this.data.metric
    const nonCompliant = this.datasets.find((ds) => ds.label === 'non-compliant')
    const targetType = this.metricType === 0 ? program.energy_metric_type : program.emission_metric_type

    // Ranked distance from target (col id = 0)
    if (this.xAxisColumnId === 0) {
      nonCompliant.data.sort((a, b) => (b.distance ?? -Infinity) - (a.distance ?? -Infinity))
      for (const [i, item] of nonCompliant.data.entries()) {
        item.x = i + 1
      }
    }

    for (const item of nonCompliant.data) {
      const annotation = this.blankAnnotation()

      item.distance = null
      // Only show whiskers for non-compliant points that violate the target.
      const belowTarget = targetType === 1 && item?.target < item?.y
      const aboveTarget = targetType === 2 && item?.target > item?.y
      const addWhisker = belowTarget || aboveTarget

      if (!addWhisker) continue

      item.distance = Math.abs(item.target - item.y)
      annotation.xMin = item.x
      annotation.xMax = item.x
      annotation.yMin = item.y
      annotation.yMax = item.target
      this.annotations[`prop${item.id}`] = annotation
    }
  }

  getValue(property: Record<string, unknown>, fn: 'startsWith' | 'endsWith', key: string) {
    const entry = Object.entries(property).find(([k]) => k[fn](key))
    return entry?.[1]
  }

  resetDatasets() {
    const isHidden = (label: InsightDatasetVisibility) => !this.datasetVisibility.includes(label)
    this.datasets = [
      { data: [], label: 'compliant', pointStyle: 'circle', pointRadius: 7, hidden: isHidden('compliant') },
      { data: [], label: 'non-compliant', pointStyle: 'triangle', pointRadius: 7, hidden: isHidden('non-compliant') },
      { data: [], label: 'unknown', pointStyle: 'rect', hidden: isHidden('unknown') },
    ]
  }

  blankAnnotation(): AnnotationOptions {
    return {
      type: 'line',
      xMin: 0,
      xMax: 0,
      yMin: 0,
      yMax: 0,
      borderColor: () => (this.scheme === 'dark' ? '#ffffffff' : '#333333'),
      borderWidth: 1,
      display: this.datasetVisibility.includes('whisker'),
      arrowHeads: {
        end: {
          display: true,
          width: 9,
          length: 0,
        },
      },
    }
  }

  toggleVisibility(idx: number, show: boolean) {
    const label = this.datasetOrder[idx]
    if (!label) return

    if (show && !this.datasetVisibility.includes(label)) {
      this.datasetVisibility.push(label)
    } else if (!show) {
      this.datasetVisibility = this.datasetVisibility.filter((value) => value !== label)
    }

    if (idx === 3) {
      this.toggleWhiskers(show)
    } else {
      this.chart.setDatasetVisibility(idx, show)
    }
    this.chart.update()
    this.persistPropertyInsightsSettings()
  }

  toggleWhiskers(show: boolean) {
    for (const key of Object.keys(this.annotations)) {
      if (key.startsWith('prop')) {
        this.annotations[key].display = show
      }
    }
  }

  downloadChart() {
    const a = document.createElement('a')
    a.href = this.chart.toBase64Image()
    a.download = `Program-${this.program.name}.png`
    a.click()
  }

  refreshChart() {
    if (!this.program) return
    this.initChart()
    this.setChart()
  }

  clearChart() {
    this.programCycles = []
    this.programXAxisColumns = [this.rankedCol]
    this.loading = false
    this.initChart()
  }

  clearLabels() {
    this.chart.data.labels = []
    this.chart.update()
  }

  sortLabels() {
    const labels = this.chart.data.labels ?? []
    const isNumeric = labels.every((l) => !isNaN(Number(l)))
    if (isNumeric) {
      labels.sort((a, b) => Number(a) - Number(b))
    } else {
      labels.sort((a, b) => naturalSort(a as string, b as string))
    }
  }

  onRowClicked({ data }: RowClickedEvent<{ id: number }>) {
    if (data.id) {
      void this._router.navigate(['/properties', data.id])
    }
  }

  openLabelModal = () => {
    if (!this.canUpdateLabels) return

    const visibleData = this.chart.data.datasets.filter((_, i) => this.chart.isDatasetVisible(i)).map((ds) => ds.data)
    if (!visibleData.length) return

    const ids = visibleData.flatMap((d: PropertyInsightPoint[]) => d).map((d) => d.id)
    this._dialog.open(LabelsModalComponent, {
      width: '50rem',
      data: {
        orgId: this.org.id,
        type: 'properties',
        viewIds: ids,
      },
    })
  }

  openProgramConfig = () => {
    if (!this.canConfigureProgram) return

    const dialogRef = this._dialog.open(ProgramConfigComponent, {
      width: '50rem',
      data: {
        filterGroups: this.filterGroups,
        cycles: this.cycles,
        programs: this.programs,
        program: this.program,
        org: this.org,
        propertyColumns: this.propertyColumns?.sort((a, b) => naturalSort(a.display_name, b.display_name)),
        xAxisColumns: this.xAxisColumns,
      },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap((programId: number) => {
          this.programChange(programId)
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  get canConfigureProgram() {
    return this.currentUser?.org_role !== 'viewer'
  }

  get canUpdateLabels() {
    return this.currentUser?.org_role !== 'viewer'
  }

  ngOnDestroy(): void {
    this._persistSettings$.complete()
    this._reset$.next()
    this._reset$.complete()
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  initChart() {
    this.chart?.destroy()
    this.chart = new Chart(this.canvas.nativeElement, {
      type: 'scatter',
      data: {
        labels: [],
        datasets: [],
      },
      options: {
        onClick: (_, elements: ActiveElement[], chart: Chart<'scatter'>) => {
          if (!elements.length) return
          const { datasetIndex, index } = elements[0]
          const raw = chart.data.datasets[datasetIndex].data[index] as PropertyInsightPoint
          const viewId = raw.id
          return void this._router.navigate(['/properties', viewId])
        },
        elements: {
          point: {
            radius: 5,
          },
        },
        plugins: {
          title: {
            display: true,
            align: 'start',
          },
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: (context: TooltipItem<'scatter'> & { raw: { name: string; id: number } }) => {
                const text: string[] = []
                // property ID / default display field
                if (context.raw.name) {
                  text.push(`Property: ${context.raw.name}`)
                } else {
                  text.push(`Property ID: ${context.raw.id}`)
                }

                // x and y axis names and values
                const [xAxisName, yAxisName] = this.getXYAxisName()
                text.push(`${xAxisName}: ${context.parsed.x}`)
                text.push(`${yAxisName}: ${context.parsed.y}`)
                return text
              },
            },
          },
          zoom: {
            limits: {
              x: { min: 'original', max: 'original', minRange: 50 },
              y: { min: 'original', max: 'original', minRange: 50 },
            },
            pan: {
              enabled: true,
              mode: 'xy',
            },
            zoom: {
              wheel: {
                enabled: true,
              },
              mode: 'xy',
            },
          },
          annotation: {
            annotations: {},
          },
        },
        scales: {
          x: {
            title: {
              text: 'X',
              display: true,
            },
            ticks: {
              callback(value) {
                return this.getLabelForValue(value as number)
              },
            },
            type: 'linear',
          },
          y: {
            type: 'linear',
            beginAtZero: true,
            position: 'left',
            display: true,
            title: {
              text: 'Y',
              display: true,
            },
          },
        },
      },
    })
  }
}
