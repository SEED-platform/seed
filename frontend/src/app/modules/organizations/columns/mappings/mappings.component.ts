import { CommonModule } from '@angular/common'
import { ChangeDetectionStrategy, Component, HostListener, inject, type OnDestroy, type OnInit, ViewEncapsulation } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type {
  CellClassParams,
  CellDoubleClickedEvent,
  ColDef,
  ColGroupDef,
  GridApi,
  GridOptions,
  GridReadyEvent,
  IRowNode,
  ValueFormatterParams,
} from 'ag-grid-community'
import { combineLatest, filter, type Observable, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Column, ColumnMapping, ColumnMappingProfile } from '@seed/api'
import { ColumnMappingProfileService, MappableColumnService } from '@seed/api'
import { DeleteModalComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { type ComponentCanDeactivate } from '@seed/guards/pending-changes.guard'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { naturalSort } from '@seed/utils'
import { ActionButtonsComponent } from './action-buttons.component'
import { CopyModalComponent } from './modal/copy-modal.component'
import { CreateModalComponent } from './modal/create-modal.component'
import { EditModalComponent } from './modal/edit-modal.component'
import { RenameModalComponent } from './modal/rename-modal.component'

type DataType = {
  id: string;
  value: string;
  type: string;
}
type RenderMapping = ColumnMapping & {
  column: Column | null;
  unit_label: string;
}

@Component({
  selector: 'seed-organizations-column-mappings',
  templateUrl: './mappings.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, SharedImports, MaterialImports, ReactiveFormsModule],
})
export class MappingsComponent implements ComponentCanDeactivate, OnDestroy, OnInit {
  private _dialog = inject(MatDialog)
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _configService = inject(ConfigService)
  private _mappableColumnService = inject(MappableColumnService)
  protected readonly _unsubscribeAll$ = new Subject<void>()
  private _gridApi!: GridApi<RenderMapping>
  orgId: number
  profiles: ColumnMappingProfile[]
  mappablePropertyColumns: Column[]
  mappableTaxlotColumns: Column[]
  selectedProfile: ColumnMappingProfile
  dataTypes: DataType[] = [
    { id: '', value: 'None', type: 'none' },
    { id: 'ft**2', value: 'square feet', type: 'area' },
    { id: 'm**2', value: 'square metres', type: 'area' },
    { id: 'kBtu/ft**2/year', value: 'kBtu/ft²/year', type: 'eui' },
    { id: 'kWh/m**2/year', value: 'kWh/m²/year', type: 'eui' },
    { id: 'GJ/m**2/year', value: 'GJ/m²/year', type: 'eui' },
    { id: 'MJ/m**2/year', value: 'MJ/m²/year', type: 'eui' },
    { id: 'kBtu/m**2/year', value: 'kBtu/m²/year', type: 'eui' },
    { id: 'MtCO2e/year', value: 'MtCO2e/year', type: 'ghg' },
    { id: 'kgCO2e/year', value: 'kgCO2e/year', type: 'ghg' },
    { id: 'kgal/ft**2/year', value: 'kgal/ft²/year', type: 'wui' },
    { id: 'gal/ft**2/year', value: 'gal/ft²/year', type: 'wui' },
    { id: 'L/m**2/year', value: 'L/m²/year', type: 'wui' },
    { id: 'MtCO2e/ft**2/year', value: 'MtCO2e/ft²/year', type: 'ghg_intensity' },
    { id: 'kgCO2e/ft**2/year', value: 'kgCO2e/ft²/year', type: 'ghg_intensity' },
    { id: 'MtCO2e/m**2/year', value: 'MtCO2e/m²/year', type: 'ghg_intensity' },
    { id: 'kgCO2e/m**2/year', value: 'kgCO2e/m²/year', type: 'ghg_intensity' },
    { id: 'kgal/year', value: 'kgal/year', type: 'water_use' },
    { id: 'gal/year', value: 'gal/year', type: 'water_use' },
    { id: 'L/year', value: 'L/year', type: 'water_use' },
  ]
  columnDefs: (ColDef<RenderMapping> | ColGroupDef<RenderMapping>)[] = [
    {
      headerName: 'SEED',
      children: [
        { headerName: 'Omit?', field: 'is_omitted', cellRenderer: 'agCheckboxCellRenderer', editable: false, width: 100 },
        {
          headerName: 'Inventory Type',
          field: 'to_table_name',
          editable: false,
          valueFormatter: (params: ValueFormatterParams) => {
            return (params.value as string)?.slice(0, -5)
          },
        },
        {
          headerName: 'SEED Header',
          field: 'to_field',
          valueFormatter: (params: ValueFormatterParams<RenderMapping>) => {
            return (params.data.column?.display_name || params.value) as string
          },
        },
        {
          headerName: 'Measurement Units',
          field: 'from_units',
          editable: false,
          valueFormatter: (params: ValueFormatterParams<RenderMapping>) => {
            return params.data.unit_label
          },
          cellClass: (params: CellClassParams<RenderMapping>) => {
            if (this.measuredColumn(params.node) && !params.data.from_units) {
              return 'bg-red-300'
            } else {
              return ''
            }
          },
        },
      ],
    },
    {
      headerName: 'Profile',
      children: [
        {
          headerName: 'Data File Header',
          field: 'from_field',
          cellClass: (params: CellClassParams<RenderMapping>) => {
            if (this.countFromFieldsInGrid(params.data.from_field) > 1) {
              return 'bg-red-300'
            } else {
              return ''
            }
          },
        },
        {
          headerName: 'Actions',
          cellRendererSelector: (_params) => {
            if (this.profileReadOnly()) {
              return undefined
            }
            return {
              component: ActionButtonsComponent,
              params: {
                onDelete: (data: ColumnMapping, node: IRowNode<RenderMapping>) => {
                  this.deleteMapping(data, node)
                },
                onEdit: (data: ColumnMapping, node: IRowNode<RenderMapping>) => {
                  this.editMapping(data, node)
                },
              },
            }
          },
        },
      ],
    },
  ]
  rowData: RenderMapping[] = []
  gridOptions: GridOptions<RenderMapping> = {
    columnDefs: this.columnDefs,
    pagination: false,
    suppressCellFocus: true,
  }
  darkMode: boolean
  gridTheme$ = this._configService.gridTheme$
  gridReady = false
  changesToSave = false

  isLoaded = false
  selectedProfileForm = new FormGroup({ selectedProfile: new FormControl<number | null>(null) })

  @HostListener('window:beforeunload')
  canDeactivate(): Observable<boolean> | boolean {
    // insert logic to check if there are pending changes here;
    // returning true will navigate without confirmation
    // returning false will show a confirm dialog before navigating away
    return false
  }

  ngOnInit(): void {
    combineLatest([
      this._mappableColumnService.taxLotColumns$,
      this._mappableColumnService.propertyColumns$,
      this._columnMappingProfileService.profiles$,
    ])
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(([taxLotColumns, propertyColumns, profiles]) => {
        this.mappableTaxlotColumns = taxLotColumns
        this.mappablePropertyColumns = propertyColumns
        this.orgId = this.mappablePropertyColumns[0].organization_id
        this.profiles = profiles.sort((a, b) => naturalSort(a.name, b.name))
        this.selectedProfile = profiles.sort((a, b) => a.id - b.id)[0]
        this.selectedProfileForm.get('selectedProfile').setValue(this.selectedProfile.id)
        this.rowData = this.buildRenderMappings(this.selectedProfile.mappings)
      })
    this.isLoaded = true
  }

  ngOnDestroy(): void {
    this._gridApi = undefined
  }

  toFieldRenderer(params: ValueFormatterParams) {
    const mapping = params.data as ColumnMapping
    const col = this.getColumn(mapping.to_table_name, params.value as string)
    if (col) {
      return col.display_name
    } else {
      return params.value as string
    }
  }

  lookupDataType(params: string): string {
    if (!params) {
      return ''
    }
    const dt = this.dataTypes.find((d) => d.id === params)
    if (dt) {
      return dt.value
    } else {
      return ''
    }
  }

  buildRenderMappings(mappings: ColumnMapping[]): RenderMapping[] {
    return mappings.map((m: ColumnMapping) => {
      const rm: RenderMapping = {
        is_omitted: m.is_omitted,
        to_field: m.to_field,
        to_table_name: m.to_table_name,
        from_units: m.from_units,
        from_field: m.from_field,
        from_field_value: m.from_field_value ? m.from_field_value : null,
        column: this.getColumn(m.to_table_name, m.to_field),
        unit_label: this.lookupDataType(m.from_units),
      }
      return rm
    })
  }

  onGridReady(params: GridReadyEvent<RenderMapping>) {
    this._gridApi = params.api
  }

  populateGrid(profile: ColumnMappingProfile) {
    const rm = this.buildRenderMappings(profile.mappings)
    this.rowData = rm
    this._gridApi.setGridOption('rowData', rm)
  }

  countFromFieldsInGrid(matchValue: string): number {
    if (!this.gridReady) {
      return 0
    }
    let count = 0
    this._gridApi.forEachNode((node: IRowNode<RenderMapping>, _index) => {
      if (node.data.from_field === matchValue) {
        count += 1
      }
    })
    return count
  }

  selectProfile(profileId?: number) {
    if (profileId === undefined) {
      profileId = this.selectedProfileForm.get('selectedProfile').value
    }
    if (profileId !== this.selectedProfile.id) {
      this.selectedProfile = this.profiles.find((p) => p.id === profileId)
    }
    this.populateGrid(this.selectedProfile)
    this.changesToSave = false
  }

  profileReadOnly() {
    if (!this.selectedProfile) {
      return true
    }
    return this.selectedProfile.profile_type === 'BuildingSync Default'
  }

  seedHeaderName(mapping: ColumnMapping): string {
    if (!this.mappablePropertyColumns || !this.mappableTaxlotColumns) {
      return ''
    }
    const col = this.getColumn(mapping.to_table_name, mapping.to_field)
    if (col) {
      return col.display_name
    }
    return mapping.to_field
  }

  getColumn(table_name: string, to_field: string): Column | null {
    if (!this.mappablePropertyColumns || !this.mappableTaxlotColumns) {
      return null
    }
    if (table_name === 'PropertyState') {
      return this.mappablePropertyColumns.find((c) => c.column_name === to_field) || null
    }
    if (table_name === 'TaxLotState') {
      return this.mappableTaxlotColumns.find((c) => c.column_name === to_field) || null
    }
    return null
  }

  measuredColumn(node: IRowNode<RenderMapping>) {
    if (!node.data.column) {
      return false
    }
    return ['area', 'eui', 'ghg', 'wui', 'ghg_intensity', 'water_use'].includes(node.data.column.data_type)
  }

  getMappingsFromGrid(): ColumnMapping[] {
    const mappings: ColumnMapping[] = []
    this._gridApi.forEachNode((rowNode, _index) => {
      mappings.push(this.buildMappingFromRowNode(rowNode))
    })
    return mappings
  }

  onCellDoubleClicked(event: CellDoubleClickedEvent<RenderMapping>): void {
    if (this.profileReadOnly() || !event.data) {
      return
    }

    this.editMapping(event.data, event.node)
  }

  deleteMapping(_mapping: ColumnMapping, node: IRowNode<RenderMapping>): void {
    this._gridApi.applyTransaction({ remove: [node.data] })
    this.changesToSave = true
  }

  editMapping(mapping: ColumnMapping, node: IRowNode<RenderMapping>): void {
    const dialogRef = this._dialog.open(EditModalComponent, {
      width: '80rem',
      data: {
        profile: this.selectedProfile,
        mapping,
        org_id: this.orgId,
        columns: [].concat(this.mappablePropertyColumns, this.mappableTaxlotColumns),
      },
    })
    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((newMapping: ColumnMapping) => {
          if (newMapping) {
            node.setData(this.buildRenderMappings([newMapping])[0])
            this.changesToSave = true
            this.selectedProfileForm.get('selectedProfile').disable()
          }
        }),
      )
      .subscribe()
  }

  create_profile = () => {
    const dialogRef = this._dialog.open(CreateModalComponent, {
      width: '80rem',
      maxHeight: '75vh',
      data: { org_id: this.orgId, columns: [].concat(this.mappablePropertyColumns, this.mappableTaxlotColumns) },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((newProfileId: number) => {
          if (newProfileId) {
            this._columnMappingProfileService.getProfiles(this.orgId).subscribe((_profiles) => {
              this.selectedProfileForm.get('selectedProfile').setValue(newProfileId)
              this.selectProfile(newProfileId)
              this._gridApi.redrawRows()
            })
          }
        }),
      )
      .subscribe()
  }

  copy_profile() {
    const dialogRef = this._dialog.open(CopyModalComponent, {
      width: '40rem',
      data: {
        profile_type: this.selectedProfile.profile_type === 'BuildingSync Default' ? 'BuildingSync Custom' : 'Normal',
        selectedProfileName: this.selectedProfile.name,
        mappings: this.getMappingsFromGrid(),
        org_id: this.orgId,
      },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((newProfileId: number) => {
          this._columnMappingProfileService.getProfiles(this.orgId).subscribe(() => {
            if (newProfileId) {
              this.selectedProfileForm.get('selectedProfile').setValue(newProfileId)
              this.selectProfile(newProfileId)
            }
          })
        }),
      )
      .subscribe()
  }

  delete() {
    const profileToDelete = this.selectedProfile
    if (profileToDelete.profile_type === 'BuildingSync Default') {
      return
    }
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Column Mapping Profile', instance: this.selectedProfile.name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        switchMap(() => this._columnMappingProfileService.delete(this.orgId, this.selectedProfile.id)),
        tap(() => {
          this.selectedProfileForm.get('selectedProfile').setValue(this.profiles.find((p) => p.id !== profileToDelete.id).id)
          this.selectProfile()
          this._columnMappingProfileService.getProfiles(this.orgId).subscribe()
        }),
      )
      .subscribe()
  }

  rename() {
    const profileToUpdate = this.selectedProfile

    const dialogRef = this._dialog.open(RenameModalComponent, {
      width: '40rem',
      data: { profile: profileToUpdate, org_id: this.orgId },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this._columnMappingProfileService.getProfiles(this.orgId).subscribe(() => {
            this.selectedProfileForm.get('selectedProfile').setValue(profileToUpdate.id)
            this.selectProfile()
          })
        }),
      )
      .subscribe()
  }

  export() {
    if (!this.selectedProfile) {
      return
    }
    const filename = `column_mapping_profile_${this.selectedProfile.id}.csv`
    this._columnMappingProfileService
      .export(this.orgId, this.selectedProfile.id)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((blob) => {
        this._downloadBlob(blob, filename)
      })
  }

  suggest() {
    const headers = this.selectedProfile.mappings.map((m) => m.from_field)
    this._columnMappingProfileService
      .suggestions(this.orgId, headers)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((suggestions) => {
        for (const k of Object.keys(suggestions)) {
          this.selectedProfile.mappings.find((m) => m.from_field === k).to_table_name = suggestions[k][0]
          this.selectedProfile.mappings.find((m) => m.from_field === k).to_field = suggestions[k][1]
        }
        this.populateGrid(this.selectedProfile)
      })
  }

  copy() {
    for (const m of this.selectedProfile.mappings) {
      m.to_field = m.from_field
    }
    this.populateGrid(this.selectedProfile)
    this.changesToSave = true
  }

  save() {
    const orgId = this.orgId
    this._columnMappingProfileService
      .updateMappings(orgId, this.selectedProfile.id, this.getMappingsFromGrid())
      .subscribe((updatedProfile) => {
        const i = this.profiles.indexOf(this.selectedProfile)
        this.profiles[i] = updatedProfile
        this.selectedProfileForm.get('selectedProfile').enable()
        this.populateGrid(this.profiles[i])
      })
  }

  cancel() {
    this.populateGrid(this.selectedProfile)
    this.changesToSave = false
    this.selectedProfileForm.get('selectedProfile').enable()
  }

  buildMappingFromRowNode(rowNode: IRowNode<RenderMapping>): ColumnMapping {
    return {
      to_field: rowNode.data.to_field,
      from_field: rowNode.data.from_field,
      from_units: rowNode.data.from_units,
      to_table_name: rowNode.data.to_table_name,
      is_omitted: rowNode.data.is_omitted,
      from_field_value: rowNode.data.from_field_value,
    }
  }

  private _downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  }
}
