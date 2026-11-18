import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { TranslocoService } from '@jsverse/transloco'
import { AgGridAngular } from 'ag-grid-angular'
import type { CellValueChangedEvent, ColDef } from 'ag-grid-community'
import type { Observable } from 'rxjs'
import { map, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Label, LabelColor } from '@seed/api'
import { LabelService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService, ConfirmationService } from '@seed/services'
import { SEEDValidators } from '@seed/validators'
import type { InventoryType } from '../inventory.types'

type LabelRow = Label & { add: boolean; remove: boolean; isApplied: boolean; isGoalApplied: boolean }

@Component({
  selector: 'seed-labels-modal',
  templateUrl: './labels-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, FormsModule, MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class LabelsModalComponent implements OnInit, OnDestroy {
  private _unsubscribeAll$ = new Subject<void>()
  private _dialogRef = inject(MatDialogRef<LabelsModalComponent>)
  private _configService = inject(ConfigService)
  private _confirmationService = inject(ConfirmationService)
  private _labelService = inject(LabelService)
  private _translocoService = inject(TranslocoService)
  colors: LabelColor[] = ['red', 'orange', 'blue', 'light blue', 'green', 'gray']
  columnDefs: ColDef[]
  existingNames: string[] = []
  gridTheme$ = this._configService.gridTheme$
  gridHeight = 0
  labels: Label[] = []
  newLabel: Label
  rowData: LabelRow[] = []

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    type: InventoryType;
    viewIds: number[];
    appliedLabelIds?: number[];
    goalLabelIds?: number[];
  }

  form = new FormGroup({
    organization_id: new FormControl(this.data.orgId),
    name: new FormControl<string>(null),
    color: new FormControl<LabelColor>('gray'),
    show_in_list: new FormControl(true),
  })

  ngOnInit(): void {
    this._labelService.labels$
      .pipe(
        tap((labels) => {
          this.labels = labels
          this.setValidator()
          this.setGrid()
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  setValidator() {
    this.existingNames = this.labels.map((g) => g.name)
    const nameCtrl = this.form.get('name')
    nameCtrl?.setValidators([SEEDValidators.uniqueValue(this.existingNames)])
  }

  setGrid() {
    this.getGridHeight()
    this.setColDefs()
    this.setRowData()
  }

  setRowData() {
    const appliedIds = this.data.appliedLabelIds
    const goalIds = this.data.goalLabelIds ?? []
    this.rowData = this.labels.map((label) => ({
      ...label,
      add: label.id === this.newLabel?.id,
      remove: false,
      isApplied: appliedIds ? appliedIds.includes(label.id) : false,
      isGoalApplied: goalIds.includes(label.id),
    }))

    this.newLabel = null
  }

  setColDefs() {
    const hasApplied = Boolean(this.data.appliedLabelIds)
    this.columnDefs = [
      {
        field: 'name',
        headerName: 'Label',
        flex: 1,
        cellRenderer: (params: { data: LabelRow }) => this.labelRenderer(params),
      },
      {
        field: 'add',
        headerName: 'Add',
        flex: 0.2,
        editable: hasApplied ? (params) => !(params.data as { isApplied: boolean }).isApplied : true,
        cellStyle: hasApplied
          ? (params) => ((params.data as { isApplied: boolean }).isApplied ? { opacity: '0.3', cursor: 'not-allowed' } : null)
          : null,
      },
      {
        field: 'remove',
        headerName: 'Remove',
        flex: 0.2,
        editable: hasApplied ? (params) => (params.data as { isApplied: boolean }).isApplied : true,
        cellStyle: hasApplied
          ? (params) => (!(params.data as { isApplied: boolean }).isApplied ? { opacity: '0.3', cursor: 'not-allowed' } : null)
          : null,
      },
    ]
  }

  labelRenderer({ data }: { data: LabelRow }) {
    let goalBadge = ''
    if (data.isGoalApplied) {
      const badgeText = this._translocoService.translate('cross-cycle')
      const badgeTitle = this._translocoService.translate('Applied by a cross-cycle data quality check from the Portfolio Summary page')
      goalBadge = `<span class="text-secondary ml-2 whitespace-nowrap text-xs italic" title="${badgeTitle}">${badgeText}</span>`
    }
    return `
      <div class="flex h-full items-center">
        <div class="label compact ${data.color} whitespace-nowrap">${data.name}</div>${goalBadge}
      </div>
    `
  }

  onCellValueChanged(event: CellValueChangedEvent): void {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    const { colDef, newValue, node } = event
    const field = colDef.field
    const otherField = field === 'add' ? 'remove' : 'add'
    const data = node.data as LabelRow

    if (newValue && data[otherField]) {
      node.setDataValue(otherField, false)
    }

    if (field === 'remove' && newValue && data.isGoalApplied) {
      this.confirmGoalLabelRemoval(data.name).subscribe((confirmed) => {
        if (!confirmed) node.setDataValue('remove', false)
      })
    }
  }

  confirmGoalLabelRemoval(labelName: string): Observable<boolean> {
    const message = this._translocoService.translate(
      '"{{labelName}}" was applied by a cross-cycle data quality check run from the Portfolio Summary page. Removing it here deletes that result. It will come back the next time the goal checks are run.',
      { labelName },
    )
    return this._confirmationService
      .open({
        title: this._translocoService.translate('Remove cross-cycle label?'),
        message,
        icon: { show: true, name: 'fa-solid:triangle-exclamation', color: 'warn' },
        actions: { confirm: { label: this._translocoService.translate('Remove'), color: 'warn' } },
      })
      .afterClosed()
      .pipe(map((result) => result === 'confirmed'))
  }

  getGridHeight() {
    this.gridHeight = Math.min(this.labels.length * 42 + 52, 500)
  }

  onSubmit() {
    const data = this.form.value as Label
    this._labelService
      .create(data)
      .pipe(
        tap((label) => {
          this.newLabel = label
        }),
        switchMap(() => this._labelService.getByOrgId(data.organization_id)),
        tap(() => {
          this.form.reset()
        }),
      )
      .subscribe()
  }

  done() {
    const { orgId, viewIds, type } = this.data
    const addLabelIds: number[] = this.rowData.filter((g) => g.add).map((g) => g.id)
    const removeLabelIds: number[] = this.rowData.filter((g) => g.remove).map((g) => g.id)

    if (!addLabelIds.length && !removeLabelIds.length) {
      this.close()
      return
    }

    this._labelService.updateLabelInventory(orgId, viewIds, type, addLabelIds, removeLabelIds).subscribe(() => {
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
