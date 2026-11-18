import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { finalize, take, tap } from 'rxjs'
import type { ReportConfiguration, ReportConfigurationUpsertPayload } from '@seed/api'
import { ReportConfigurationService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-report-config-modal',
  templateUrl: './report-config-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class ReportConfigModalComponent {
  private _dialogRef = inject(MatDialogRef<ReportConfigModalComponent>)
  private _reportConfigService = inject(ReportConfigurationService)

  data = inject(MAT_DIALOG_DATA) as {
    action: 'new' | 'rename' | 'delete';
    config: ReportConfiguration;
    orgId: number;
  }

  nameControl = new FormControl(this.data.action === 'rename' ? (this.data.config?.name ?? '') : '', Validators.required)
  submitting = false

  get title() {
    const titles: Record<string, string> = {
      new: 'Create Report Configuration',
      rename: 'Rename Report Configuration',
      delete: 'Delete Report Configuration',
    }
    return titles[this.data.action]
  }

  get isDisabled() {
    if (this.submitting) return true
    if (this.data.action === 'delete') return false
    if (this.data.action === 'rename') return this.nameControl.invalid || this.nameControl.value === this.data.config?.name
    return this.nameControl.invalid
  }

  onSubmit() {
    this.submitting = true
    const { action, config, orgId } = this.data

    if (action === 'new') {
      const payload: ReportConfigurationUpsertPayload = {
        name: this.nameControl.value,
        x_column: config?.x_column ?? null,
        y_column: config?.y_column ?? null,
        access_level_instance_id: config?.access_level_instance_id ?? null,
        access_level_depth: config?.access_level_depth ?? null,
        cycles: config?.cycles ?? [],
        filter_group_id: config?.filter_group_id ?? null,
      }
      this._reportConfigService
        .create(orgId, payload)
        .pipe(
          take(1),
          tap((result) => {
            this._dialogRef.close(result)
          }),
          finalize(() => (this.submitting = false)),
        )
        .subscribe()
    } else if (action === 'rename') {
      const payload: ReportConfigurationUpsertPayload = {
        name: this.nameControl.value,
        x_column: config.x_column,
        y_column: config.y_column,
        access_level_instance_id: config.access_level_instance_id,
        access_level_depth: config.access_level_depth,
        cycles: config.cycles,
        filter_group_id: config.filter_group_id,
      }
      this._reportConfigService
        .update(orgId, config.id, payload)
        .pipe(
          take(1),
          tap((result) => {
            this._dialogRef.close(result)
          }),
          finalize(() => (this.submitting = false)),
        )
        .subscribe()
    } else if (action === 'delete') {
      this._reportConfigService
        .delete(orgId, config.id)
        .pipe(
          take(1),
          tap(() => {
            this._dialogRef.close('deleted')
          }),
          finalize(() => (this.submitting = false)),
        )
        .subscribe()
    }
  }

  close() {
    this._dialogRef.close()
  }
}
