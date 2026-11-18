import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { GroupsService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

export type DeleteMeterDialogData = {
  orgId: number;
  groupId: number;
  meter: {
    id: number;
    alias: string;
    type: string;
  };
}

@Component({
  selector: 'seed-delete-meter-dialog',
  templateUrl: './delete-meter-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class DeleteMeterDialogComponent {
  private _data = inject(MAT_DIALOG_DATA) as DeleteMeterDialogData
  private _dialogRef = inject(MatDialogRef<DeleteMeterDialogComponent>)
  private _groupsService = inject(GroupsService)

  meterName = this._data.meter.alias || `${this._data.meter.type} (ID: ${this._data.meter.id})`
  submitted = false

  confirm() {
    if (this.submitted) return
    this.submitted = true

    this._groupsService.deleteMeter(this._data.orgId, this._data.groupId, this._data.meter.id).subscribe({
      next: () => {
        this._dialogRef.close(true)
      },
      error: () => {
        this.submitted = false
      },
    })
  }
}
