import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { Dataset } from '@seed/api'
import { DatasetService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'

@Component({
  selector: 'seed-dataset-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class FormModalComponent implements OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _datasetService = inject(DatasetService)
  data = inject(MAT_DIALOG_DATA) as { orgId: number; dataset: Dataset; existingNames?: string[] }
  form = new FormGroup({
    name: new FormControl('', [Validators.required, SEEDValidators.uniqueValue(this.data.existingNames)]),
  })
  create = this.data.dataset ? false : true

  ngOnInit() {
    if (this.data.dataset) {
      this.form.patchValue({ name: this.data.dataset.name })
    }
  }

  onSubmit() {
    if (!this.form.valid) return

    if (this.create) {
      this._datasetService.create(this.data.orgId, this.form.value.name).subscribe(() => {
        this.dismiss()
      })
    } else {
      this._datasetService.update(this.data.orgId, this.data.dataset.id, this.form.value.name).subscribe(() => {
        this.dismiss()
      })
    }
  }

  dismiss() {
    this._dialogRef.close()
  }
}
