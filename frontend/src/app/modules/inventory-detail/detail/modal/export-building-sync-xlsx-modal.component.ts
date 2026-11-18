import type { AfterViewInit, OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import type { MatStepper } from '@angular/material/stepper'
import { catchError, EMPTY, Subject, switchMap, take, takeUntil } from 'rxjs'
import type { ProgressResponse } from '@seed/api'
import { CacheService, InventoryService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-export-building-sync-xlsx-modal',
  templateUrl: './export-building-sync-xlsx-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class ExportBuildingSyncXlsxModalComponent implements AfterViewInit, OnDestroy {
  @ViewChild('stepper') stepper!: MatStepper
  private _cacheService = inject(CacheService)
  private _dialogRef = inject(MatDialogRef<ExportBuildingSyncXlsxModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _snackBar = inject(SnackBarService)
  private _uploaderService = inject(UploaderService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewId: number; profileId: number | null }

  progressBarObj = this._uploaderService.defaultProgressBarObj

  ngAfterViewInit(): void {
    this.stepper.next()
    this._inventoryService
      .startInventoryExport(this.data.orgId, {
        export_type: 'xlsx',
        filename: `buildingsync_property_${this.data.viewId}.xlsx`,
        ids: [this.data.viewId],
        include_meter_readings: false,
        include_notes: false,
        profile_id: this.data.profileId,
      })
      .pipe(
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn: ({ unique_id }: ProgressResponse) => {
              this._cacheService
                .getCacheEntry(this.data.orgId, unique_id)
                .pipe(take(1))
                .subscribe((response: { data: string }) => {
                  const blob = this._uploaderService.stringToBlob(response.data, 'xlsx')
                  const a = document.createElement('a')
                  a.href = URL.createObjectURL(blob)
                  a.download = `buildingsync_property_${this.data.viewId}.xlsx`
                  a.click()
                  URL.revokeObjectURL(a.href)
                  this._snackBar.success('BuildingSync Excel file downloaded.')
                  this.close()
                })
            },
            progressBarObj: this.progressBarObj,
          }),
        ),
        takeUntil(this._unsubscribeAll$),
        catchError(() => EMPTY),
      )
      .subscribe()
  }

  close(): void {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
