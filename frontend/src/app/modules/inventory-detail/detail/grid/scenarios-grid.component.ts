import { CommonModule } from '@angular/common'
import type { OnChanges, OnDestroy, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { TranslocoDirective, TranslocoService } from '@jsverse/transloco'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, GridApi, GridReadyEvent, ICellRendererParams } from 'ag-grid-community'
import { Subject, switchMap, takeUntil } from 'rxjs'
import type { Measure, Scenario } from '@seed/api'
import { ScenarioService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { ViewResponse } from 'app/modules/inventory/inventory.types'

type MeasureStatusCount = { status: string; label: string; count: number; classes: string }

// Colors follow the measure's progress: proposed/evaluated are neutral-to-warm, completed/verified green,
// discarded/unsatisfactory muted or red. Class strings are literal so Tailwind's scanner keeps them.
const MEASURE_STATUS_CLASSES: Record<string, string> = {
  Proposed: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  Evaluated: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
  Selected: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  Initiated: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
  Discarded: 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  'In Progress': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  Completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  MV: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
  Verified: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
  Unsatisfactory: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}
const MEASURE_STATUS_DEFAULT_CLASSES = 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'

const escapeHtml = (value: string): string =>
  value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')

const statusChipHtml = (status: string, label: string): string => {
  const classes = MEASURE_STATUS_CLASSES[status] ?? MEASURE_STATUS_DEFAULT_CLASSES
  return `<span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold leading-none ${classes}">${escapeHtml(label)}</span>`
}

@Component({
  selector: 'seed-inventory-detail-scenarios-grid',
  templateUrl: './scenarios-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, AgGridAngular, MaterialImports, TranslocoDirective],
})
export class ScenariosGridComponent implements OnChanges, OnDestroy {
  @Input() orgId: number
  @Input() view: ViewResponse
  @Input() viewId: number
  @Output() refreshView = new EventEmitter<null>()
  private _configService = inject(ConfigService)
  private _scenarioService = inject(ScenarioService)
  private _transloco = inject(TranslocoService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  measureColumnDefs: ColDef[] = []
  gridTheme$ = this._configService.gridTheme$
  scenarios: Scenario[]
  rowDataEntries: { date: string; rawDate: number; rowData: Scenario[] }[] = []

  private _gridApis = new Map<number, GridApi>()

  constructor() {
    // Build columns up front so the grid never initializes before the first language load resolves
    this.setMeasureColumnDefs()
    // ag-grid headers are plain strings, so they can't re-render themselves the way *transloco can.
    // langChanges$ fires before the new language file is fetched, so wait for the load to finish.
    this._transloco.langChanges$
      .pipe(
        switchMap((lang) => this._transloco.load(lang)),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe(() => {
        this.setMeasureColumnDefs()
      })
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.view) {
      this.initScenarios()
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  initScenarios() {
    this.scenarios = this.view.state.scenarios
    this.setGrid()
  }

  setMeasureColumnDefs() {
    const t = (key: string) => this._transloco.translate(key)
    const currencyColumn = (field: string, headerName: string, minWidth: number): ColDef => ({
      field,
      headerName,
      flex: 1,
      minWidth,
      type: 'numericColumn',
      valueFormatter: (params) => this.formatCurrency(params),
    })
    const numericColumn = (field: string, headerName: string, minWidth: number): ColDef => ({
      field,
      headerName,
      flex: 1,
      minWidth,
      type: 'numericColumn',
      valueFormatter: (params) => this.formatNumber(params),
    })
    // Order mirrors the legacy property detail measure table so the two UIs stay comparable
    this.measureColumnDefs = [
      { field: 'category', headerName: t('Category'), flex: 1, minWidth: 130 },
      { field: 'display_name', headerName: t('Name'), flex: 2, minWidth: 180 },
      {
        field: 'recommended',
        headerName: t('Recommended'),
        flex: 1,
        minWidth: 140,
        // Without this ag-grid infers a boolean type and swaps in a read-only checkbox, which both
        // ignores the formatter below and looks editable in a read-only grid.
        cellDataType: 'text',
        valueFormatter: (params) => this.formatBoolean(params),
      },
      {
        field: 'implementation_status',
        headerName: t('Status'),
        flex: 1,
        minWidth: 150,
        cellRenderer: ({ value }: ICellRendererParams) => this.statusRenderer({ value }),
      },
      { field: 'category_affected', headerName: t('Category Affected'), flex: 1, minWidth: 170 },
      currencyColumn('cost_installation', t('Installation Cost'), 160),
      currencyColumn('cost_material', t('Material Cost'), 150),
      currencyColumn('cost_residual_value', t('Residual Value'), 150),
      currencyColumn('cost_total_first', t('First Cost'), 130),
      currencyColumn('annual_cost_savings', t('Annual Cost Savings'), 180),
      numericColumn('annual_electricity_savings', t('Electricity Savings (kBtu)'), 200),
      numericColumn('annual_peak_electricity_reduction', t('Peak Electricity Reduction (kW)'), 230),
      numericColumn('annual_natural_gas_savings', t('Natural Gas Savings (kBtu)'), 210),
      currencyColumn('cost_capital_replacement', t('Capital Replacement Cost'), 200),
      { field: 'description', headerName: t('Description'), flex: 2, minWidth: 200 },
      numericColumn('useful_life', t('Useful Life (years)'), 160),
    ]
  }

  onGridReady({ api }: GridReadyEvent, scenarioId: number): void {
    this._gridApis.set(scenarioId, api)
    // The grid is created while the panel is still opening, so refresh once layout has settled
    this._refreshGridCells(scenarioId)
  }

  onPanelExpanded(scenarioId: number): void {
    this._refreshGridCells(scenarioId)
  }

  // Sum of the scenario's measures' MeasureTotalFirstCost; null when no measure reports a cost
  getTotalFirstCost(scenario: Scenario): number | null {
    return this.sumMeasureField(scenario, 'cost_total_first')
  }

  // BuildingSync reports annual cost savings on the package and/or on each measure
  getTotalAnnualCostSavings(scenario: Scenario): number | null {
    return this.getScenarioOrMeasureTotal(scenario, 'annual_cost_savings')
  }

  getElectricitySavings(scenario: Scenario): number | null {
    return this.getScenarioOrMeasureTotal(scenario, 'annual_electricity_savings')
  }

  getPeakElectricityReduction(scenario: Scenario): number | null {
    return this.getScenarioOrMeasureTotal(scenario, 'annual_peak_electricity_reduction')
  }

  getNaturalGasSavings(scenario: Scenario): number | null {
    return this.getScenarioOrMeasureTotal(scenario, 'annual_natural_gas_savings')
  }

  /**
   * Prefer the package-level (scenario) value when BuildingSync provides one, otherwise roll up
   * the scenario's measures. Audit Template files often report savings at only one of the two levels.
   */
  getScenarioOrMeasureTotal(scenario: Scenario, field: string): number | null {
    const scenarioValue = scenario?.[field]
    if (typeof scenarioValue === 'number') return scenarioValue
    return this.sumMeasureField(scenario, field)
  }

  sumMeasureField(scenario: Scenario, field: string): number | null {
    const values = (scenario?.measures ?? []).map((measure) => measure[field]).filter((value): value is number => typeof value === 'number')
    if (!values.length) return null
    return values.reduce((sum, value) => sum + value, 0)
  }

  formatCurrency = ({ value }: { value: unknown }): string => {
    if (typeof value !== 'number') return this._transloco.translate('N/A')
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
  }

  formatNumber = ({ value }: { value: unknown }): string => {
    if (typeof value !== 'number') return this._transloco.translate('N/A')
    return value.toLocaleString('en-US', { maximumFractionDigits: 1 })
  }

  formatBoolean = ({ value }: { value: unknown }): string => {
    if (typeof value !== 'boolean') return this._transloco.translate('N/A')
    return this._transloco.translate(value ? 'Yes' : 'No')
  }

  // Counts of each implementation status in the scenario, so they can be shown as colored chips
  getMeasureStatuses(scenario: Scenario): MeasureStatusCount[] {
    const counts = new Map<string, number>()
    for (const measure of scenario?.measures ?? []) {
      const status = measure.implementation_status || 'Unknown'
      counts.set(status, (counts.get(status) ?? 0) + 1)
    }
    return [...counts.entries()].map(([status, count]) => ({
      status,
      label: this._transloco.translate(status),
      count,
      classes: MEASURE_STATUS_CLASSES[status] ?? MEASURE_STATUS_DEFAULT_CLASSES,
    }))
  }

  // Renders the measure's status as the same colored chip used in the scenario header rollup
  statusRenderer = ({ value }: { value: unknown }): string => {
    if (typeof value !== 'string' || !value) return ''
    return statusChipHtml(value, this._transloco.translate(value))
  }

  deleteScenario(id: number, name: string): void {
    const message = this._transloco.translate('Are you sure you want to delete scenario "{{scenarioName}}"?', { scenarioName: name })
    if (confirm(message)) {
      this._scenarioService.deleteScenario(this.orgId, this.viewId, id).subscribe(() => {
        this.refreshView.emit(null)
      })
    }
  }

  setGrid() {
    this.rowDataEntries = []
    // The API returns the most recently imported state as `state`; `history` only holds *prior*
    // states, so looking at history alone hides the newest scenarios entirely.
    const states = [{ date_edited: this.view.date_edited, state: this.view.state }, ...this.view.history]
    for (const { date_edited, state } of states) {
      const date = new Date(date_edited).toLocaleString('en-US', {})
      const entry = { date, rawDate: date_edited, rowData: this.getScenarios(state.scenarios) }
      if (entry.rowData.length) this.rowDataEntries.push(entry)
    }
    this.rowDataEntries.sort((a, b) => b.rawDate - a.rawDate)
  }

  // Scenario type isn't stored, so retain scenarios that may only have package-level savings
  getScenarios(scenarios: Scenario[]): Scenario[] {
    return scenarios ?? []
  }

  getMeasuresHeight(measures: Measure[]): number {
    // Extra room for the horizontal scrollbar the wider column set introduces
    return Math.min((measures?.length ?? 0) * 42 + 52, 300) + 16
  }

  // ag-grid drops cell renderer output (the status chip) for cells it creates before the grid has a
  // size, leaving them blank until something forces a re-render. These panels start collapsed, so
  // every grid here hits that; refreshing once the panel is open fills the cells in.
  private _refreshGridCells(scenarioId: number): void {
    setTimeout(() => {
      const api = this._gridApis.get(scenarioId)
      if (api && !api.isDestroyed()) api.refreshCells({ force: true })
    })
  }
}
