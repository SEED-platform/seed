import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { ColumnMapping, ColumnMappingProfile, ColumnMappingProfileType } from '@seed/api'
import { ColumnMappingProfileService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { SEEDValidators } from '@seed/validators'

@Component({
  selector: 'seed-data-mapping-create-profile',
  templateUrl: './create-profile.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class CreateProfileComponent {
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _dialogRef = inject(MatDialogRef<CreateProfileComponent>)

  profileName = ''
  profile: ColumnMappingProfile

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    profileType: ColumnMappingProfileType;
    mappings: ColumnMapping[];
    existingNames: string[];
  }
  form = new FormGroup({
    name: new FormControl('', [Validators.required, SEEDValidators.uniqueValue(this.data.existingNames)]),
  })

  onSubmit() {
    this.profile = {
      name: this.form.value.name,
      profile_type: this.data.profileType,
      mappings: this.data.mappings,
    } as ColumnMappingProfile

    this._columnMappingProfileService.create(this.data.orgId, this.profile).subscribe(() => {
      this.close()
    })
  }

  close() {
    this._dialogRef.close()
  }
}
