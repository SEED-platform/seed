import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Subject } from 'rxjs'
import { type EmailTemplate, PostOfficeService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-email-templates-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class FormModalComponent implements OnDestroy, OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _postOfficeService = inject(PostOfficeService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  template: EmailTemplate
  create = true
  data = inject(MAT_DIALOG_DATA) as { template: EmailTemplate | null; organization_id: number }
  form = new FormGroup({
    name: new FormControl('', Validators.required),
  })

  ngOnInit(): void {
    if (this.data.template) {
      this.template = this.data.template
      this.create = false
      this.form.get('name').patchValue(this.template.name)
    }
  }

  onSubmit() {
    if (this.template) {
      // rename
      this.template.name = this.form.get('name').value
      this._postOfficeService.update(this.data.organization_id, this.template).subscribe((t) => {
        this._dialogRef.close(t.id)
      })
    } else {
      this._postOfficeService.create(this.data.organization_id, this.form.get('name').value).subscribe((t) => {
        this._dialogRef.close(t.id)
      })
    }
  }

  close() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
