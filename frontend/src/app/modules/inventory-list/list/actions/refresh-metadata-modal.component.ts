import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { combineLatest, filter, finalize, Subject, switchMap, takeUntil, tap } from 'rxjs'
import { InventoryService } from '@seed/api'
import { ModalHeaderComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-refresh-metadata-modal',
  templateUrl: './refresh-metadata-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ProgressBarComponent],
})
export class RefreshMetadataModalComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<RefreshMetadataModalComponent>)
  private _inventoryService = inject(InventoryService)
  private _snackBar = inject(SnackBarService)
  private _uploaderService = inject(UploaderService)
  private _unsubscribeAll$ = new Subject<void>()
  currentTime: string
  inProgress = false
  progressBarObj = this._uploaderService.defaultProgressBarObj
  progressKey: string

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    type: InventoryType;
  }

  ngOnInit() {
    setInterval(() => {
      this.currentTime = new Date().toLocaleTimeString()
    }, 1000)
  }

  refresh() {
    this.inProgress = true
    this._inventoryService
      .startRefreshMetadata(this.data.orgId)
      .pipe(
        switchMap(({ progress_key }) => this.pollRefresh(progress_key)),
        filter(([_, progressResponse]) => progressResponse.progress >= 100),
        tap(() => {
          this._snackBar.success('Success')
          this.close(true)
        }),
        takeUntil(this._unsubscribeAll$),
        finalize(() => {
          this.inProgress = false
        }),
      )
      .subscribe()
  }

  pollRefresh(progress_key: string) {
    const { orgId, type, viewIds } = this.data
    const [propertyViews, taxlotViews] = type == 'taxlots' ? [[], viewIds] : [viewIds, []]

    return combineLatest([
      this._inventoryService.refreshMetadata(orgId, propertyViews, taxlotViews, progress_key),
      this._uploaderService.checkProgressLoop({
        progressKey: progress_key,
        progressBarObj: this.progressBarObj,
      }),
    ])
  }

  close(success = false): void {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
