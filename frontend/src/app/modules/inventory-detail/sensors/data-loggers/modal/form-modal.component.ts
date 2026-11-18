import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { tap } from 'rxjs'
import type { DataLogger } from '@seed/api'
import { SensorService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'

@Component({
  selector: 'seed-inventory-detail-data-loggers-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ReactiveFormsModule],
})
export class FormModalComponent implements OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _sensorService = inject(SensorService)
  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewId: number;
    dataLogger: DataLogger;
    existingDisplayNames: string[];
  }
  form = new FormGroup({
    display_name: new FormControl('', [Validators.required, SEEDValidators.uniqueValue(this.data.existingDisplayNames)]),
    identifier: new FormControl('', Validators.required),
    location_description: new FormControl('', Validators.required),
    manufacturer_name: new FormControl('', Validators.required),
    model_name: new FormControl('', Validators.required),
    serial_number: new FormControl('', Validators.required),
  })
  create = !this.data.dataLogger

  ngOnInit() {
    this.patchForm()
  }

  patchForm() {
    if (!this.create) {
      this.form.patchValue(this.data.dataLogger)
    }
  }

  onSubmit() {
    if (this.create) {
      this._sensorService
        .createDataLogger(this.data.orgId, this.data.viewId, this.form.value as DataLogger)
        .pipe(
          tap(() => {
            this.close(true)
          }),
        )
        .subscribe()
    } else {
      this._sensorService
        .updateDataLogger(this.data.orgId, this.data.viewId, this.data.dataLogger.id, this.form.value as DataLogger)
        .pipe(
          tap(() => {
            this.close(true)
          }),
        )
        .subscribe()
    }
  }

  close(success = false) {
    this._dialogRef.close(success)
  }
}
