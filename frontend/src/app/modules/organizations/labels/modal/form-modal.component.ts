import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Subject } from 'rxjs'
import type { Label } from '@seed/api'
import { LabelService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-labels-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class FormModalComponent implements OnDestroy, OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _labelService = inject(LabelService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  label: Label
  colors = ['blue', 'gray', 'green', 'light blue', 'orange', 'red']
  create = true
  data = inject(MAT_DIALOG_DATA) as { label: Label | null; organization_id: number }
  form = new FormGroup({
    name: new FormControl('', Validators.required),
    color: new FormControl<string | null>(null, Validators.required),
    organization_id: new FormControl<number | null>(null),
    show_in_list: new FormControl(false),
    id: new FormControl<number | null>(null),
  })

  ngOnInit(): void {
    this.create = !('id' in this.data.label)
    this.form.patchValue(this.data.label)
  }

  onSubmit() {
    const data = this.form.value as Label
    if (data.id) {
      this._labelService.update(data).subscribe()
    } else {
      this._labelService.create(data).subscribe()
    }
    this.close()
  }

  close() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
