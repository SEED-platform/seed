import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { map } from 'rxjs'
import { type ColumnMapping, type ColumnMappingProfile, ColumnMappingProfileService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-column-mappings-copy-modal',
  templateUrl: './copy-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ReactiveFormsModule],
})
export class CopyModalComponent implements OnInit {
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _dialogRef = inject(MatDialogRef<CopyModalComponent>)
  errorMessage: string
  inProgress = false
  profile: ColumnMappingProfile
  form = new FormGroup({
    name: new FormControl('', [Validators.required]),
  })
  data = inject(MAT_DIALOG_DATA) as { selectedProfileName: string; mappings: ColumnMapping[]; org_id: number; profile_type: string }

  ngOnInit(): void {
    this.profile = { profile_type: this.data.profile_type, name: '', id: null, mappings: [] }
    this.profile.mappings = this.data.mappings
  }

  onSubmit() {
    this.profile.name = this.form.get('name').value
    this._columnMappingProfileService
      .create(this.data.org_id, this.profile)
      .pipe(
        map((response) => {
          this._dialogRef.close(response.data.id)
        }),
      )
      .subscribe()
  }

  close() {
    this._dialogRef.close()
  }
}
