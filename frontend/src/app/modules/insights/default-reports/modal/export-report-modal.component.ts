import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { finalize, take, tap } from 'rxjs'
import { InventoryReportService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-export-report-modal',
  templateUrl: './export-report-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class ExportReportModalComponent {
  private _dialogRef = inject(MatDialogRef<ExportReportModalComponent>)
  private _reportService = inject(InventoryReportService)

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    xVar: string;
    xLabel: string;
    yVar: string;
    yLabel: string;
    cycleIds: number[];
    filterGroupId: number | null;
  }

  nameControl = new FormControl('', Validators.required)
  exporting = false

  exportData() {
    let filename = this.nameControl.value
    if (!filename) return

    if (!filename.endsWith('.xlsx')) filename += '.xlsx'
    this.exporting = true

    this._reportService
      .exportReportData(
        this.data.orgId,
        this.data.xVar,
        this.data.xLabel,
        this.data.yVar,
        this.data.yLabel,
        this.data.cycleIds,
        this.data.filterGroupId,
      )
      .pipe(
        take(1),
        tap((blob) => {
          const a = document.createElement('a')
          const url = URL.createObjectURL(blob)
          a.href = url
          a.download = filename
          a.click()
          URL.revokeObjectURL(url)
          this._dialogRef.close()
        }),
        finalize(() => (this.exporting = false)),
      )
      .subscribe()
  }

  close() {
    this._dialogRef.close()
  }
}
