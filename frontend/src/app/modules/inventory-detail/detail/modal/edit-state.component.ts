import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import type { FormGroup } from '@angular/forms'
import { FormBuilder, FormControl, ReactiveFormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { Column } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import type { InventoryType, ViewResponse } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-edit-state',
  templateUrl: './edit-state.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ReactiveFormsModule],
})
export class EditStateModalComponent implements OnInit {
  private _dialogRef = inject(MatDialogRef<EditStateModalComponent>)
  private _fb = inject(FormBuilder)

  data = inject(MAT_DIALOG_DATA) as {
    columns: Column[];
    orgId: number;
    view: ViewResponse;
    matchingColumns: string[];
    extraDataColumnNames: Set<string>;
  }

  changedData: Record<string, unknown> = { extra_data: {} }
  changedFields = new Set<string>()
  displayNameMap: Record<string, string> = {}
  form: FormGroup<Record<string, FormControl>>
  labelWidth: number
  preSave = true
  type: InventoryType

  ngOnInit() {
    this.setForm()
  }

  /*
   * Generates the form for the main state based on the profile columns
   * detects value changes and highlights border
   */
  setForm() {
    const controls: Record<string, FormControl> = {}
    const state = this.data.view.state
    const filteredCols = this.data.columns.filter((c) => !c.derived_column)

    for (const { column_name, display_name } of filteredCols) {
      const isExtraData = this.data.extraDataColumnNames.has(column_name)
      const displayName = display_name || column_name
      const value = isExtraData ? state.extra_data[column_name] : state[column_name]
      const control = new FormControl(value)

      control.valueChanges.subscribe(() => {
        this.changedFields.add(column_name)
      })

      controls[column_name] = control
      this.displayNameMap[column_name] = displayName
    }
    this.form = this._fb.group(controls)
  }

  get orderedColumns() {
    const keys = Object.keys(this.form.controls)
    return keys.sort((a, b) => naturalSort(a, b))
  }

  onSave() {
    for (const [key, control] of Object.entries(this.form.controls)) {
      if (!control.dirty) continue

      const target = this.data.extraDataColumnNames.has(key) ? this.changedData.extra_data : this.changedData
      const value: unknown = control.value === '' ? null : control.value
      target[key] = value
    }

    this.preSave = false
  }

  onSubmit() {
    this._dialogRef.close(this.changedData)
  }

  dismiss() {
    this._dialogRef.close()
  }
}
