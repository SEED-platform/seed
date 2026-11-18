import type { ElementRef, OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { Router, RouterLink } from '@angular/router'
import { Chart } from 'chart.js'
import { combineLatest, filter, finalize, Subject, take, takeUntil, tap } from 'rxjs'
import type {
  AccessLevelsByDepth,
  AggregatedChartPoint,
  AxisVariable,
  Column,
  Cycle,
  FilterGroup,
  Organization,
  ReportAxisData,
  ReportChartPoint,
  ReportConfiguration,
  ReportPropertyCount,
} from '@seed/api'
import {
  CycleService,
  FilterGroupService,
  InventoryReportService,
  OrganizationService,
  ReportConfigurationService,
  UserService,
} from '@seed/api'
import { PageComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ExportReportModalComponent, ReportConfigModalComponent } from './modal'

const DEFAULT_COLORS = ['#458cc8', '#779e1c', '#f2c41d', '#939495', '#c83737', '#f18630']

const UNIT_MAPPINGS: Record<string, string> = {
  'ft**2': 'ft²',
  'm**2': 'm²',
  'kBtu/ft**2/year': 'kBtu/sq. ft./year',
  'GJ/m**2/year': 'GJ/m²/year',
  'MJ/m**2/year': 'MJ/m²/year',
  'kWh/m**2/year': 'kWh/m²/year',
  'kBtu/m**2/year': 'kBtu/m²/year',
}

@Component({
  selector: 'seed-default-reports',
  templateUrl: './default-reports.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, ProgressBarComponent, ReactiveFormsModule, RouterLink],
})
export class DefaultReportsComponent implements OnInit, OnDestroy {
  @ViewChild('scatterCanvas', { static: true }) scatterCanvasRef!: ElementRef<HTMLCanvasElement>
  @ViewChild('barCanvas', { static: true }) barCanvasRef!: ElementRef<HTMLCanvasElement>
  private _cycleService = inject(CycleService)
  private _dialog = inject(MatDialog)
  private _filterGroupService = inject(FilterGroupService)
  private _organizationService = inject(OrganizationService)
  private _reportConfigService = inject(ReportConfigurationService)
  private _reportService = inject(InventoryReportService)
  private _router = inject(Router)
  private _unsubscribeAll$ = new Subject<void>()
  private _userService = inject(UserService)
  private _userAccessLevelInstanceId: number
  private _usersDepth = 0
  private _accessLevelInstancesByDepth: AccessLevelsByDepth = {}

  // Charts
  scatterChart: Chart
  barChart: Chart
  chart1Title = ''
  chart2Title = ''
  scatterStatusMessage = 'No Data'
  aggStatusMessage = 'No Data'
  scatterLoading = false
  aggLoading = false

  // Data
  axisData: ReportAxisData = {}
  cycles: Cycle[] = []
  filterGroups: FilterGroup[] = []
  isOwner = false
  levelNames: string[] = []
  org: Organization
  potentialLevelInstances: { id: number; name: string }[] = []
  reportConfigurations: ReportConfiguration[] = []
  scatterPropertyCounts: ReportPropertyCount[] = []
  aggPropertyCounts: ReportPropertyCount[] = []
  xAxisVars: AxisVariable[] = []
  yAxisVars: AxisVariable[] = []

  // Report config state
  selectedConfigId: number | null = 0
  currentConfig: ReportConfiguration | null = null
  reportModified = false
  orderByX: Record<string, number> = {}

  form = new FormGroup({
    accessLevelIndex: new FormControl(0),
    accessLevelInstanceId: new FormControl<number | null>(null),
    cycles: new FormControl<number[]>([]),
    filterGroupId: new FormControl<number | null>(null),
    xAxis: new FormControl<string | null>(null),
    yAxis: new FormControl<string | null>(null),
    aggregationType: new FormControl('Sum'),
  })

  get hasChartData() {
    return this.scatterChart?.data?.datasets?.[0]?.data?.length > 0
  }

  objectKeys = Object.keys

  ngOnInit() {
    this.initCharts()
    this.watchFormModified()
    this.getDependencies()
  }

  getDependencies() {
    combineLatest({
      org: this._organizationService.currentOrganization$,
      cycles: this._cycleService.cycles$,
      filterGroups: this._filterGroupService.filterGroups$,
      reportConfigs: this._reportConfigService.reportConfigurations$,
      currentUser: this._userService.currentUser$,
      accessLevelTree: this._organizationService.accessLevelTree$,
      accessLevelInstancesByDepth: this._organizationService.accessLevelInstancesByDepth$,
    })
      .pipe(
        tap(({ org, cycles, filterGroups, reportConfigs, currentUser, accessLevelTree, accessLevelInstancesByDepth }) => {
          this.org = org
          this.cycles = cycles
          this.filterGroups = filterGroups
          this.reportConfigurations = reportConfigs
          this.isOwner = currentUser?.org_role === 'owner'
          this._userAccessLevelInstanceId = currentUser?.ali_id
          this._accessLevelInstancesByDepth = accessLevelInstancesByDepth

          // Calculate user's depth
          const depthEntry = Object.entries(accessLevelInstancesByDepth).find(
            ([, instances]) => instances.length === 1 && instances[0].id === this._userAccessLevelInstanceId,
          )
          this._usersDepth = depthEntry ? Number(depthEntry[0]) : 0

          this.levelNames = accessLevelTree.accessLevelNames.slice(Math.max(0, this._usersDepth - 1))
          this.buildAxisVars()
          this.initAccessLevel()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  buildAxisVars() {
    if (!this.org) return
    const euiUnit = UNIT_MAPPINGS[this.org.display_units_eui] ?? this.org.display_units_eui
    const areaUnit = UNIT_MAPPINGS[this.org.display_units_area] ?? this.org.display_units_area

    const parseAxisLabel = (col: Column) => {
      const name = col.display_name || col.column_name
      if (col.column_name.includes('eui')) return `${name} (${euiUnit})`
      if (col.column_name.includes('area')) return `${name} (${areaUnit})`
      return name
    }

    this.xAxisVars = (this.org.default_reports_x_axis_options ?? []).map((col) => ({
      name: col.display_name || col.column_name,
      label: col.display_name || col.column_name,
      varName: col.column_name,
      axisLabel: parseAxisLabel(col),
    }))

    this.yAxisVars = [
      { name: 'Count', label: 'Count', varName: 'Count', axisLabel: 'Count' },
      ...(this.org.default_reports_y_axis_options ?? []).map((col) => ({
        name: col.display_name || col.column_name,
        label: col.display_name || col.column_name,
        varName: col.column_name,
        axisLabel: parseAxisLabel(col),
      })),
    ]

    // Add current access level group-by option
    this.appendAccessLevelAxis()

    // Set defaults if not set
    if (!this.form.value.xAxis && this.xAxisVars.length) {
      this.form.patchValue({ xAxis: this.xAxisVars[0].varName }, { emitEvent: false })
    }
    if (!this.form.value.yAxis && this.yAxisVars.length) {
      this.form.patchValue({ yAxis: this.yAxisVars[0].varName }, { emitEvent: false })
    }
  }

  appendAccessLevelAxis() {
    const index = this.form.value.accessLevelIndex ?? 0
    const groupByLevel = this.levelNames[index] ?? this.levelNames[this.levelNames.length - 1]
    if (!groupByLevel) return

    // Remove previous access-level axis if present
    this.xAxisVars = this.xAxisVars.filter((v) => !this.levelNames.includes(v.varName))
    this.xAxisVars.push({
      name: groupByLevel,
      label: groupByLevel,
      varName: groupByLevel,
      axisLabel: groupByLevel,
    })
  }

  initAccessLevel() {
    const index = this.form.value.accessLevelIndex ?? 0
    const depth = index + this._usersDepth
    this.potentialLevelInstances = this._accessLevelInstancesByDepth[depth] ?? []

    if (!this.form.value.accessLevelInstanceId && this._userAccessLevelInstanceId) {
      this.form.patchValue({ accessLevelInstanceId: this._userAccessLevelInstanceId }, { emitEvent: false })
    }
  }

  watchFormModified() {
    this.form.valueChanges.pipe(takeUntil(this._unsubscribeAll$)).subscribe(() => {
      this.reportModified = true
    })

    this.form
      .get('accessLevelIndex')
      ?.valueChanges.pipe(
        tap((index) => {
          const depth = (index ?? 0) + this._usersDepth
          this.potentialLevelInstances = this._accessLevelInstancesByDepth[depth] ?? []
          this.form.patchValue({ accessLevelInstanceId: null })
          this.appendAccessLevelAxis()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  // --- Chart initialization ---

  initCharts() {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    this.scatterChart = new Chart(this.scatterCanvasRef.nativeElement, {
      type: 'scatter',
      data: { datasets: [{ data: [], pointBackgroundColor: [] }] },
      options: {
        onClick: (_event, activeElements, chart) => {
          if (!activeElements.length) return
          const { datasetIndex, index } = activeElements[0]
          const raw = chart.data.datasets[datasetIndex].data[index] as unknown as ReportChartPoint
          if (raw?.id) void this._router.navigate(['/properties', raw.id])
        },
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: 20 },
        scales: {
          x: { display: true, title: { display: true }, suggestedMin: 0 },
          y: {
            display: true,
            title: { display: true },
            ticks: {
              callback(value) {
                return this.getLabelForValue(value as number)
              },
            },
          },
        },
        elements: { point: { radius: 5, backgroundColor: '#458CC8' } },
        plugins: {
          legend: { display: false },
          tooltip: {
            displayColors: false,
            mode: 'index',
            callbacks: {
              title: (ctx) => (ctx[0]?.raw as ReportChartPoint)?.display_name ?? '',
              label: (ctx) => {
                const xLabel = this.getSelectedAxisVar('x')?.label ?? 'X'
                const yLabel = this.getSelectedAxisVar('y')?.label ?? 'Y'
                return [`${xLabel}: ${(ctx.raw as ReportChartPoint).x}`, `${yLabel}: ${ctx.parsed.y}`]
              },
            },
          },
          zoom: {
            pan: { enabled: true },
            zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'xy' },
          },
        },
      },
    })

    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    this.barChart = new Chart(this.barCanvasRef.nativeElement, {
      type: 'bar',
      data: { labels: [], datasets: [{ data: [], backgroundColor: [] }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: 20 },
        indexAxis: 'x',
        scales: {
          x: { display: true, type: 'category', title: { display: true }, ticks: {} },
          y: { display: true, title: { display: true }, ticks: { precision: 0 } },
        },
        elements: { bar: { backgroundColor: '#458CC8' } },
        plugins: {
          legend: { display: false },
          tooltip: {
            displayColors: false,
            mode: 'index',
            callbacks: {
              label: (ctx) => {
                const xLabel = this.getSelectedAxisVar('x')?.label ?? 'X'
                const yLabel = this.getSelectedAxisVar('y')?.label ?? 'Y'
                return [`${xLabel}: ${ctx.label}`, `${yLabel}: ${ctx.raw as number}`]
              },
            },
          },
          zoom: {
            pan: { enabled: true },
            zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: 'xy' },
          },
        },
      },
    })
  }

  // --- Data loading ---

  updateChartData() {
    this.clearChartData()
    this.scatterStatusMessage = 'Loading data...'
    this.aggStatusMessage = 'Loading data...'
    this.reportModified = false
    this.updateChartTitlesAndAxes()
    this.getScatterData()
    this.getAggData()
  }

  clearChartData() {
    this.scatterPropertyCounts = []
    this.aggPropertyCounts = []
    this.axisData = {}
    this.scatterChart.data.datasets[0].data = []
    ;(this.scatterChart.data.datasets[0] as unknown as Record<string, unknown>).pointBackgroundColor = []
    this.scatterChart.update()
    this.barChart.data.labels = []
    this.barChart.data.datasets[0].data = []
    ;(this.barChart.data.datasets[0] as { backgroundColor?: unknown }).backgroundColor = []
    this.barChart.update()
  }

  updateChartTitlesAndAxes() {
    const xItem = this.getSelectedAxisVar('x')
    const yItem = this.getSelectedAxisVar('y')
    if (!xItem || !yItem) return

    this.chart1Title = `${xItem.label} vs ${yItem.label}`
    this.chart2Title = `${xItem.label} vs ${yItem.label} (${this.form.value.aggregationType})`

    const scatterScales = this.scatterChart.options.scales as Record<string, { title: { text: string } }>
    scatterScales.x.title.text = xItem.axisLabel
    scatterScales.y.title.text = yItem.axisLabel

    const barScales = this.barChart.options.scales as Record<string, { title: { text: string } }>
    barScales.x.title.text = xItem.axisLabel
    barScales.y.title.text = yItem.axisLabel
  }

  getScatterData() {
    const { xAxis, yAxis, cycles, accessLevelInstanceId, filterGroupId } = this.form.value
    if (!xAxis || !yAxis) {
      this.scatterStatusMessage = 'No Axis'
      return
    }
    if (!cycles?.length) {
      this.scatterStatusMessage = 'No Cycles Selected'
      return
    }
    this.scatterLoading = true

    this._reportService
      .getReportData(this.org.id, xAxis, yAxis, cycles, accessLevelInstanceId, filterGroupId)
      .pipe(
        take(1),
        finalize(() => {
          this.scatterLoading = false
        }),
        tap((data) => {
          const colorMap = this.mapColors(data.property_counts)
          this.scatterPropertyCounts = data.property_counts

          // Determine axis types
          const allNumericY = data.chart_data.every((d) => typeof d.y === 'number')
          const allNumericX = data.chart_data.every((d) => typeof d.x === 'number')

          if (allNumericX) {
            const xValues = data.chart_data.map((d) => d.x as number)
            const xMin = Math.min(...xValues)
            const xMax = Math.max(...xValues)
            this.scatterChart.options.scales.x.type = 'linear'
            this.scatterChart.options.scales.x.min = xMin - Math.round(Math.abs(xMin * 0.005))
            this.scatterChart.options.scales.x.max = xMax + Math.round(Math.abs(xMax * 0.005))

            if (xAxis === 'year_built') {
              this.scatterChart.options.scales.x.ticks = { callback: (value) => String(value) }
            }
          } else {
            const uniqueLabels = [...new Set(data.chart_data.map((d) => String(d.x)))].sort()
            this.scatterChart.options.scales.x = {
              type: 'category',
              labels: uniqueLabels,
              title: { display: true, text: this.getSelectedAxisVar('x')?.axisLabel ?? '' },
            }
          }

          this.scatterChart.options.scales.y.type = allNumericY ? 'linear' : 'category'
          if (yAxis === 'year_built') {
            this.scatterChart.options.scales.y.ticks = {
              callback: (value) => String(value),
            }
          }

          this.scatterChart.data.datasets[0].data = data.chart_data as never[]
          const pointColors = data.chart_data.map((d) => colorMap.get(d.yr_e) ?? '#458cc8')
          ;(this.scatterChart.data.datasets[0] as unknown as Record<string, unknown>).pointBackgroundColor = pointColors
          this.scatterChart.update()

          this.axisData = data.axis_data ?? {}
          this.scatterStatusMessage = data.chart_data.length ? '' : 'No Data'
        }),
      )
      .subscribe({
        error: () => {
          this.scatterStatusMessage = 'Data Load Error'
        },
      })
  }

  getAggData() {
    const { xAxis, yAxis, cycles, accessLevelInstanceId, filterGroupId, aggregationType } = this.form.value
    if (!xAxis || !yAxis) {
      this.aggStatusMessage = 'No Axis'
      return
    }
    if (!cycles?.length) {
      this.aggStatusMessage = 'No Cycles Selected'
      return
    }
    this.aggLoading = true

    // Note: the AngularJS code swaps x/y for the aggregated endpoint
    this._reportService
      .getAggregatedReportData(this.org.id, yAxis, xAxis, cycles, accessLevelInstanceId, filterGroupId, aggregationType ?? 'Sum')
      .pipe(
        take(1),
        finalize(() => {
          this.aggLoading = false
        }),
        tap((data) => {
          const isCategory = data.chart_data.every((d) => typeof d.y === 'number') ? 'linear' : 'category'
          if (isCategory === 'category') {
            const mostRecentYearEnd = Math.max(...data.chart_data.map((d) => Number(d.yr_e)))
            const recentData = data.chart_data.filter((d) => d.yr_e === String(mostRecentYearEnd))
            this.orderByX = recentData
              .sort((a, b) => (a.x < b.x ? 1 : -1))
              .reduce<Record<string, number>>((acc, curr, i) => {
                acc[curr.y as string] = i
                return acc
              }, {})

            data.chart_data.sort((a, b) => {
              if (a.y === b.y) return a.yr_e < b.yr_e ? 1 : -1
              return (this.orderByX[a.y as string] ?? 0) > (this.orderByX[b.y as string] ?? 0) ? 1 : -1
            })
          }

          const colorMap = this.mapColors(data.property_counts)
          this.aggPropertyCounts = data.property_counts

          this.barChart.options.scales.y.min = undefined
          this.barChart.options.scales.y.max = undefined
          this.barChart.data.labels = data.chart_data.map((d: AggregatedChartPoint) => d.y as string)
          this.barChart.data.datasets[0].data = data.chart_data.map((d: AggregatedChartPoint) => d.x as number)
          ;(this.barChart.data.datasets[0] as { backgroundColor?: unknown }).backgroundColor = data.chart_data.map(
            (d: AggregatedChartPoint) => colorMap.get(d.yr_e) ?? '#458cc8',
          )
          this.barChart.update()

          this.aggStatusMessage = data.chart_data.length ? '' : 'No Data'
        }),
      )
      .subscribe({
        error: () => {
          this.aggStatusMessage = 'Data Load Error'
        },
      })
  }

  // --- Helpers ---

  getSelectedAxisVar(axis: 'x' | 'y'): AxisVariable | undefined {
    const varName = axis === 'x' ? this.form.value.xAxis : this.form.value.yAxis
    const vars = axis === 'x' ? this.xAxisVars : this.yAxisVars
    return vars.find((v) => v.varName === varName)
  }

  mapColors(propertyCounts: ReportPropertyCount[]): Map<string, string> {
    const colorMap = new Map<string, string>()
    for (const [i, count] of propertyCounts.entries()) {
      const color = DEFAULT_COLORS[i % DEFAULT_COLORS.length]
      count.color = color
      colorMap.set(count.yr_e, color)
    }
    return colorMap
  }

  formatStatValue(axisKey: string, value: number): string {
    if (axisKey === 'Year Built') return String(value)
    if (value == null) return ''
    return typeof value === 'number' ? value.toFixed(2) : String(value)
  }

  resetScatterZoom() {
    this.scatterChart?.resetZoom()
  }

  resetBarZoom() {
    this.barChart?.resetZoom()
  }

  // --- Report Configuration ---

  changeReportConfig(configId: number) {
    this.selectedConfigId = configId
    this.currentConfig = this.reportConfigurations.find((c) => c.id === configId) ?? null
    if (!this.currentConfig) return

    const accessLevelIndex = Math.max(0, (this.currentConfig.access_level_depth ?? 0) - this._usersDepth)

    this.form.patchValue(
      {
        xAxis: this.currentConfig.x_column,
        yAxis: this.currentConfig.y_column,
        cycles: this.currentConfig.cycles ?? [],
        accessLevelIndex,
        accessLevelInstanceId: this.currentConfig.access_level_instance_id,
        filterGroupId: this.currentConfig.filter_group_id,
      },
      { emitEvent: true },
    )

    this.reportModified = false
    this.updateChartData()
  }

  saveReportConfig() {
    if (!this.currentConfig?.id) return

    const { xAxis, yAxis, accessLevelInstanceId, accessLevelIndex, cycles, filterGroupId } = this.form.value
    const payload = {
      name: this.currentConfig.name,
      x_column: xAxis,
      y_column: yAxis,
      access_level_instance_id: accessLevelInstanceId,
      access_level_depth: (accessLevelIndex ?? 0) + this._usersDepth,
      cycles: cycles ?? [],
      filter_group_id: filterGroupId,
    }

    this._reportConfigService
      .update(this.org.id, this.currentConfig.id, payload)
      .pipe(
        take(1),
        tap(() => (this.reportModified = false)),
      )
      .subscribe()
  }

  newConfig() {
    const { xAxis, yAxis, accessLevelInstanceId, accessLevelIndex, cycles, filterGroupId } = this.form.value
    const configData: ReportConfiguration = {
      id: null,
      name: '',
      x_column: xAxis,
      y_column: yAxis,
      access_level_instance_id: accessLevelInstanceId,
      access_level_depth: (accessLevelIndex ?? 0) + this._usersDepth,
      cycles: cycles ?? [],
      filter_group_id: filterGroupId,
    }

    const dialogRef = this._dialog.open(ReportConfigModalComponent, {
      width: '30rem',
      data: { action: 'new', config: configData, orgId: this.org.id },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap((result: ReportConfiguration) => {
          this.selectedConfigId = result.id
          this.currentConfig = result
          this.reportModified = false
        }),
      )
      .subscribe()
  }

  renameConfig() {
    if (!this.currentConfig) return

    const dialogRef = this._dialog.open(ReportConfigModalComponent, {
      width: '30rem',
      data: { action: 'rename', config: this.currentConfig, orgId: this.org.id },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap((result: ReportConfiguration) => {
          this.currentConfig = result
        }),
      )
      .subscribe()
  }

  deleteConfig() {
    if (!this.currentConfig) return

    const dialogRef = this._dialog.open(ReportConfigModalComponent, {
      width: '30rem',
      data: { action: 'delete', config: this.currentConfig, orgId: this.org.id },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap(() => {
          this.selectedConfigId = 0
          this.currentConfig = null
          this.reportModified = false
        }),
      )
      .subscribe()
  }

  // --- Export ---

  openExportModal() {
    const xItem = this.getSelectedAxisVar('x')
    const yItem = this.getSelectedAxisVar('y')
    if (!xItem || !yItem) return

    this._dialog.open(ExportReportModalComponent, {
      width: '30rem',
      data: {
        orgId: this.org.id,
        xVar: yItem.varName,
        xLabel: yItem.label,
        yVar: xItem.varName,
        yLabel: xItem.label,
        cycleIds: this.form.value.cycles ?? [],
        filterGroupId: this.form.value.filterGroupId,
      },
    })
  }

  downloadCharts() {
    for (const [chart, name] of [
      [this.barChart, 'default_report_bar.png'],
      [this.scatterChart, 'default_report_scatter.png'],
    ] as const) {
      const canvas = chart.canvas
      const tempCanvas = document.createElement('canvas')
      tempCanvas.width = canvas.width
      tempCanvas.height = canvas.height
      const ctx = tempCanvas.getContext('2d')
      if (!ctx) continue
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height)
      ctx.drawImage(canvas, 0, 0)

      const a = document.createElement('a')
      a.href = tempCanvas.toDataURL('image/png')
      a.download = name
      a.click()
    }
  }

  ngOnDestroy() {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
    this.scatterChart?.destroy()
    this.barChart?.destroy()
  }
}
