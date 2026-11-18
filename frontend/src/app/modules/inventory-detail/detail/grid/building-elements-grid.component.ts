import { AsyncPipe } from '@angular/common'
import type { OnChanges, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, GridApi, GridReadyEvent, ITooltipParams } from 'ag-grid-community'
import { forkJoin, map } from 'rxjs'
import type { PropertyElement, UniformatLookup } from '@seed/api'
import { PropertyElementService, UniformatService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'

@Component({
  selector: 'seed-inventory-detail-building-elements-grid',
  templateUrl: './building-elements-grid.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AsyncPipe, MaterialImports],
})
export class BuildingElementsGridComponent implements OnChanges {
  @Input() orgId: number
  @Input() propertyId: number
  private _configService = inject(ConfigService)
  private _elementService = inject(PropertyElementService)
  private _uniformatService = inject(UniformatService)

  columnDefs: ColDef[] = []
  elements: PropertyElement[] = []
  gridApi: GridApi
  // Extend base theme with alternating row color
  gridTheme$ = this._configService.gridTheme$.pipe(map((t) => t.withParams({ oddRowBackgroundColor: 'rgba(0,0,0,0.04)' })))
  loading = true

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.propertyId && this.orgId && this.propertyId) {
      this.loadData()
    }
  }

  loadData(): void {
    this.loading = true
    forkJoin({
      elements: this._elementService.getElements(this.orgId, this.propertyId),
      uniformat: this._uniformatService.getUniformat(),
    }).subscribe({
      next: ({ elements, uniformat }) => {
        this.elements = elements
        this.buildColumnDefs(elements, uniformat)
        this.loading = false
      },
      error: () => {
        this.loading = false
      },
    })
  }

  buildColumnDefs(elements: PropertyElement[], uniformat: UniformatLookup): void {
    const extraKeys = [...new Set(elements.flatMap((e) => Object.keys(e.extra_data ?? {})))]

    this.columnDefs = [
      {
        field: 'code',
        headerName: 'Uniformat Category',
        flex: 2,
        valueGetter: ({ data }: { data: PropertyElement }) => uniformat[data?.code]?.category ?? data?.code,
        tooltipValueGetter: ({ data }: ITooltipParams<PropertyElement>) => `${this.buildHierarchy(data?.code, uniformat)} (${data?.code})`,
      },
      { field: 'description', headerName: 'Description', flex: 2 },
      { field: 'installation_date', headerName: 'Installation Date', flex: 1 },
      {
        field: 'condition_index',
        headerName: 'Condition Index',
        flex: 1,
        valueFormatter: ({ value }: { value: number | null }) => (value != null ? value.toFixed(2) : ''),
      },
      {
        field: 'remaining_service_life',
        headerName: 'Remaining Service Life',
        flex: 1,
        valueFormatter: ({ value }: { value: number | null }) => (value != null ? value.toFixed(2) : ''),
      },
      {
        field: 'replacement_cost',
        headerName: 'Replacement Cost',
        flex: 1,
        valueFormatter: ({ value }: { value: number | null }) => (value != null ? `$${Math.round(value).toLocaleString()}` : ''),
      },
      ...extraKeys.map((key) => ({
        headerName: key,
        flex: 1,
        valueGetter: ({ data }: { data: PropertyElement }) => data?.extra_data?.[key] ?? '',
      })),
    ]
  }

  buildHierarchy(code: string, lookup: UniformatLookup): string {
    if (!code || !lookup[code]) return code ?? ''
    const { category, parent } = lookup[code]
    return parent ? `${this.buildHierarchy(parent, lookup)} → ${category}` : category
  }

  getGridHeight(): number {
    return Math.min(this.elements.length * 42 + 52, 500)
  }

  onGridReady(agGrid: GridReadyEvent): void {
    this.gridApi = agGrid.api
    if (this.columnDefs.length) {
      this.gridApi.sizeColumnsToFit()
    }
  }
}
