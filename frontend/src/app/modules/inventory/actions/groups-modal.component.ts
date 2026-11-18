import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellValueChangedEvent, ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import { Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { CurrentUser, InventoryGroup } from '@seed/api'
import { GroupsService, OrganizationService, UserService } from '@seed/api'
import { AlertComponent, ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { SEEDValidators } from '@seed/validators'
import type { InventoryDisplayType, InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-groups-modal',
  templateUrl: './groups-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AlertComponent, CommonModule, FormsModule, MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class GroupsModalComponent implements OnDestroy, OnInit {
  private _dialogRef = inject(MatDialogRef<GroupsModalComponent>)
  private _configService = inject(ConfigService)
  private _groupsService = inject(GroupsService)
  private _organizationService = inject(OrganizationService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  aliIds: number[] = []
  aliId: number
  // aliIds: number[] = []
  currentUser: CurrentUser
  existingNames: string[] = []
  gridTheme$ = this._configService.gridTheme$
  groups: InventoryGroup[] = []
  aliGroups: (InventoryGroup & { add: boolean; remove: boolean })[] = []
  gridApi: GridApi
  columnDefs: ColDef[] = []
  allSameAli = true
  loading = true

  data = inject(MAT_DIALOG_DATA) as { orgId: number; type: InventoryType; viewIds: number[] }

  form = new FormGroup({
    name: new FormControl('', Validators.required), // existing names set when data is fetched
    organization: new FormControl(this.data.orgId),
    inventory_type: new FormControl<InventoryDisplayType>(this.data.type === 'taxlots' ? 'Tax Lot' : 'Property'),
    access_level_instance: new FormControl<number | null>(null, Validators.required),
  })

  ngOnInit(): void {
    const { orgId, type, viewIds } = this.data
    this._groupsService.list(orgId)
    this._organizationService
      .filterAccessLevelsByViews(orgId, type, viewIds)
      .pipe(
        tap((aliIds) => {
          this.aliIds = aliIds
          this.setGrid()
        }),
        switchMap(() => this._groupsService.groups$),
        tap((groups) => {
          this.setGroups(groups)
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  setGroups(groups: InventoryGroup[]) {
    this.groups = groups
    this.existingNames = groups.map((g) => g.name)
    const nameCtrl = this.form.get('name')
    nameCtrl?.setValidators([Validators.required, SEEDValidators.uniqueValue(this.existingNames)])

    this.setRowData()
    this.aliId = this.aliGroups[0]?.access_level_instance
    this.allSameAli = this.aliGroups.every((g) => g.access_level_instance === this.aliId)

    if (this.allSameAli) {
      this.form.patchValue({ access_level_instance: this.aliId ?? this.aliIds[0] })
    }
    this.loading = false
  }

  setGrid() {
    this.setRowData()
    const showMembership = this.data.viewIds.length === 1
    this.columnDefs = [
      { field: 'name', headerName: 'Group Name', flex: 1 },
      { field: 'access_level_instance_data.name', headerName: 'Access Level Instance' },
      {
        field: 'inventory_list',
        headerName: 'Inventory',
        flex: 0.5,
        valueFormatter: ({ data }: { data: InventoryGroup }) => String(data.inventory_list.length),
      },
      {
        field: 'add',
        headerName: 'Add',
        flex: 0.5,
        editable: showMembership ? (params) => this.allSameAli && !(params.data as { isMember: boolean }).isMember : this.allSameAli,
        headerClass: () => (this.allSameAli ? '' : 'text-secondary'),
        cellStyle: showMembership
          ? (params) => ((params.data as { isMember: boolean }).isMember ? { opacity: '0.3', cursor: 'not-allowed' } : null)
          : null,
      },
      {
        field: 'remove',
        headerName: 'Remove',
        flex: 0.5,
        editable: showMembership ? (params) => (params.data as { isMember: boolean }).isMember : true,
        cellStyle: showMembership
          ? (params) => (!(params.data as { isMember: boolean }).isMember ? { opacity: '0.3', cursor: 'not-allowed' } : null)
          : null,
      },
    ]
  }

  setRowData() {
    const singleViewId = this.data.viewIds.length === 1 ? this.data.viewIds[0] : null
    this.aliGroups = this.groups
      .filter((g) => this.aliIds.includes(g.access_level_instance))
      .map((group) => ({
        ...group,
        add: false,
        remove: false,
        isMember: singleViewId !== null ? group.views_list.includes(singleViewId) : false,
      }))
  }

  onCellValueChanged(event: CellValueChangedEvent): void {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    const { colDef, newValue, node } = event
    const field = colDef.field
    const otherField = field === 'add' ? 'remove' : 'add'
    const data = node.data as InventoryGroup & { add: boolean; remove: boolean }

    if (newValue && data[otherField]) {
      node.setDataValue(otherField, false)
    }
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
  }

  onSubmit() {
    this._groupsService
      .create(this.data.orgId, this.form.value as unknown as InventoryGroup)
      .pipe(take(1))
      .subscribe()
  }

  done() {
    const { orgId, viewIds, type } = this.data
    const groupType = type === 'taxlots' ? 'tax_lot' : 'property'
    const addGroupIds: number[] = this.aliGroups.filter((g) => g.add).map((g) => g.id)
    const removeGroupIds: number[] = this.aliGroups.filter((g) => g.remove).map((g) => g.id)

    if (!addGroupIds.length && !removeGroupIds.length) {
      this.close()
      return
    }

    this._groupsService.bulkUpdate(orgId, addGroupIds, removeGroupIds, viewIds, groupType).subscribe(() => {
      this.close(true)
    })
  }

  close(success = false) {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
