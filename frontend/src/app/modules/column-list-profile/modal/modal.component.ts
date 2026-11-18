import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { EMPTY, finalize, switchMap, tap } from 'rxjs'
import type { Column } from '@seed/api'
import { InventoryService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryDisplayType, InventoryType, Profile, ProfileLocation, ProfileModalMode } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-column-list-profile-modal',
  templateUrl: './modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class ModalComponent {
  private _dialogRef = inject(MatDialogRef<ModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _snackBar = inject(SnackBarService)

  data = inject(MAT_DIALOG_DATA) as {
    columns: Column[];
    cycleId: number;
    inventoryType: InventoryType;
    mode: ProfileModalMode;
    orgId: number;
    profile: Profile;
    profiles: Profile[];
    location: ProfileLocation;
    type: InventoryDisplayType;
  }

  existingNames = this.data.profiles?.map((p) => p.name).filter((name) => name !== this.data.profile?.name) ?? []

  form = new FormGroup({
    name: new FormControl('', [Validators.required, SEEDValidators.uniqueValue(this.existingNames)]),
  })

  errorMessage = false
  inProgress = false

  get createMode() {
    const populateCreate = this.data.mode === 'populate' && !this.data.profile
    return this.data.mode === 'create' || populateCreate
  }

  get populateMode() {
    return this.data.mode === 'populate' && this.data.profile
  }

  close(message = null) {
    this._dialogRef.close(message)
  }

  dismiss() {
    this._dialogRef.close()
  }

  onPopulated() {
    this.inProgress = true
    const displayType = this.data.inventoryType === 'taxlots' ? 'Tax Lot' : 'Property'
    const { orgId, profile, cycleId } = this.data

    this._inventoryService
      .updateProfileToShowPopulatedColumns(orgId, profile.id, cycleId, displayType)
      .pipe(
        switchMap((profile) => this.setOrder(profile)),
        tap(() => {
          this._snackBar.success('Profile updated')
        }),
        finalize(() => {
          setTimeout(() => {
            this.inProgress = false
          }, 1000)
          this.close(profile.id)
        }),
      )
      .subscribe()
  }

  setOrder(profile: Profile) {
    if (!profile.columns.some((c) => !c.order)) return EMPTY
    profile.columns = profile.columns.map((c, idx) => ({ ...c, order: idx + 1 }))
    return this._inventoryService.updateColumnListProfile(this.data.orgId, this.data.profile.id, profile)
  }

  onCreate() {
    const data = {
      name: this.form.get('name')?.value,
      profile_location: this.data.location,
      inventory_type: this.data.type,
      columns: this.data.columns,
      derived_columns: [],
    }

    this._inventoryService
      .createColumnListProfile(this.data.orgId, data)
      .pipe(
        tap((profile) => {
          this.data.profile = profile
          // do not close if its a show populated columns request
          if (this.data.mode === 'create') {
            this.close(profile.id)
          }
        }),
      )
      .subscribe()
  }

  onRename() {
    this.data.profile.name = this.form.get('name')?.value
    this._inventoryService.updateColumnListProfile(this.data.orgId, this.data.profile.id, this.data.profile).subscribe(() => {
      this.close(this.data.profile.id)
    })
  }
}
