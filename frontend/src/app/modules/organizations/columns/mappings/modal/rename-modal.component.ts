import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { type ColumnMappingProfile, ColumnMappingProfileService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-column-mappings-rename-modal',
  templateUrl: './rename-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ReactiveFormsModule],
})
export class RenameModalComponent implements OnInit {
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _dialogRef = inject(MatDialogRef<RenameModalComponent>)
  errorMessage: string
  inProgress = false
  profile: ColumnMappingProfile
  form = new FormGroup({
    name: new FormControl('', [Validators.required]),
  })
  data = inject(MAT_DIALOG_DATA) as { profile: ColumnMappingProfile; org_id: number }

  ngOnInit(): void {
    this.profile = this.data.profile
    this.form.get('name').setValue(this.profile.name)
  }

  onSubmit() {
    this.profile.name = this.form.get('name').value
    this._columnMappingProfileService.update(this.data.org_id, this.profile).subscribe(() => {
      this.close()
    })
  }

  close() {
    this._dialogRef.close()
  }
}
