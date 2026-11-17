import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from '@angular/material/dialog'
import { finalize, Subject, switchMap, take, tap } from 'rxjs'
import { ConfigService, DataQualityService } from '@seed/api'
import { ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services/uploader'
import { DQCResultsModalComponent } from 'app/modules/data-quality'
import type { InventoryType } from 'app/modules/inventory/inventory.types'
import { RefreshMetadataModalComponent } from 'app/modules/inventory-list/list/actions'

@Component({
  selector: 'seed-inventory-more-actions-modal',
  templateUrl: './more-actions-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ProgressBarComponent, DQCResultsModalComponent],
})
export class MoreActionsModalComponent implements OnDestroy {
  private _dataQualityService = inject(DataQualityService)
  private _deploymentConfigService = inject(ConfigService)
  private _dialog = inject(MatDialog)
  private _uploaderService = inject(UploaderService)
  private _dialogRef = inject(MatDialogRef<MoreActionsModalComponent>)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as { viewIds: number[]; orgId: number; type: InventoryType }
  errorMessage = false
  progressBarObj = this._uploaderService.defaultProgressBarObj
  showProgress = false
  progressTitle = ''

  actionsColumn1 = [
    { name: 'Analysis: Run', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Audit Template: Export', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Audit Template: Update', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Change Access Level', action: this.tempAction, disabled: !this.data.viewIds.length },
    {
      name: 'Data Quality Check',
      action: () => {
        this.dataQualityCheck()
      },
      disabled: !this.data.viewIds.length,
    },
    { name: 'Delete', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Derived Data: Update', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Email', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Export', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'FEMP CTS Reporting Export', action: this.tempAction, disabled: !this.data.viewIds.length },
  ]
  actionsColumn2 = [
    { name: 'Geocode', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Groups: Add / Remove', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Labels: Add / Remove', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'Merge', action: this.tempAction, disabled: !this.data.viewIds.length },
    {
      name: 'Set Update Time to Now',
      action: () => {
        this.openSetUpdateToNowModal()
      },
      disabled: !this.data.viewIds.length,
    },
    { name: 'Salesforce: Update', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'UBID: Add / Update', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'UBID: Compare', action: this.tempAction, disabled: !this.data.viewIds.length },
    { name: 'UBID: Decode', action: this.tempAction, disabled: !this.data.viewIds.length },
  ]

  constructor() {
    this._deploymentConfigService.config$.pipe(take(1)).subscribe(({ integrations }) => {
      if (!integrations.salesforce) this.actionsColumn2 = this.actionsColumn2.filter(({ name }) => name !== 'Salesforce: Update')
    })
  }

  tempAction() {
    console.log('temp action')
  }

  dataQualityCheck() {
    const [propertyViewIds, taxlotViewIds] = this.data.type === 'properties' ? [this.data.viewIds, []] : [[], this.data.viewIds]
    this.progressBarObj.statusMessage = 'Running Data Quality Check...'
    this.showProgress = true
    this._dataQualityService
      .startDataQualityCheckForOrg(this.data.orgId, propertyViewIds, taxlotViewIds, null)
      .pipe(
        take(1),
        switchMap(({ progress_key }) => {
          return this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            progressBarObj: this.progressBarObj,
          })
        }),
        tap(({ unique_id }) => {
          this.openDataQualityResultsModal(Number(unique_id))
        }),
        finalize(() => {
          this.showProgress = false
        }),
      )
      .subscribe()
  }

  openSetUpdateToNowModal() {
    const dialogRef = this._dialog.open(RefreshMetadataModalComponent, {
      width: '40rem',
      data: { orgId: this.data.orgId, viewIds: this.data.viewIds, type: this.data.type },
    })
    dialogRef.afterClosed().subscribe((refreshed) => {
      if (refreshed) this.close(true)
    })
  }

  openDataQualityResultsModal(dqcId: number) {
    this._dialog.open(DQCResultsModalComponent, {
      width: '50rem',
      data: { orgId: this.data.orgId, dqcId },
    })

    this.close(true)
  }

  close(refresh = false) {
    this._dialogRef.close(refresh)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
