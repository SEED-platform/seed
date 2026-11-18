import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import type { AbstractControl, AsyncValidatorFn, ValidationErrors } from '@angular/forms'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { Observable } from 'rxjs'
import { catchError, map, of, tap } from 'rxjs'
import type { Ubid, UbidDetails } from '@seed/api'
import { UbidService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-ubids-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class FormModalComponent implements OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _ubidService = inject(UbidService)

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewId: number;
    stateId: number;
    ubid: Ubid;
    type: InventoryType;
    existingUbids: string[];
  }
  form!: FormGroup

  ngOnInit() {
    this.form = new FormGroup({
      ubid: new FormControl<string | null>(null, {
        validators: [Validators.required, SEEDValidators.uniqueValue(this.data.existingUbids)],
        asyncValidators: [this.validUbid(this.data.orgId)],
      }),
      preferred: new FormControl(false, Validators.required),
    })
    if (this.data.ubid) {
      setTimeout(() => {
        // prevent ExpressionChangedAfterItHasBeenCheckedError
        const { ubid, preferred } = this.data.ubid
        this.form.patchValue({ ubid, preferred })
      })
    }
  }

  onSubmit() {
    const preferred = this.form.get('preferred').value as boolean
    const ubidDetails: UbidDetails = {
      ubid: this.form.get('ubid').value as string,
      preferred,
    }

    if (this.data.ubid) {
      this._ubidService
        .update(this.data.orgId, this.data.viewId, this.data.ubid.id, ubidDetails, this.data.type)
        .pipe(
          tap(() => {
            this.close(preferred)
          }),
        )
        .subscribe()
    } else {
      const inventoryKey = this.data.type === 'taxlots' ? 'taxlot' : 'property'
      ubidDetails[inventoryKey] = this.data.stateId
      this._ubidService
        .create(this.data.orgId, this.data.viewId, ubidDetails, this.data.type)
        .pipe(
          tap(() => {
            this.close(preferred)
          }),
        )
        .subscribe()
    }
  }

  validUbid(orgId: number): AsyncValidatorFn {
    return (control: AbstractControl): Observable<ValidationErrors | null> => {
      return this._ubidService.validate(orgId, control.value as string).pipe(
        map((isValid) => (isValid ? null : { invalidUbid: true })),
        catchError(() => of({ invalidUbid: true })),
      )
    }
  }

  close(preferred = false) {
    this._dialogRef.close(preferred)
  }
}
