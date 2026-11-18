import type { OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import type { MatDialogRef } from '@angular/material/dialog'
import { MatDialog } from '@angular/material/dialog'
import { TranslocoDirective } from '@jsverse/transloco'
import type { GridApi } from 'ag-grid-community'
import { filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Cycle, Organization } from '@seed/api'
import { AuditTemplateService, InventoryService, OrganizationService } from '@seed/api'
import { DeleteModalComponent, MenuItemComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { ModalComponent } from 'app/modules/column-list-profile/modal/modal.component'
import { DQCStartModalComponent } from 'app/modules/data-quality'
import {
  AliChangeModalComponent,
  AnalysisRunModalComponent,
  ExportModalComponent,
  GroupsModalComponent,
  LabelsModalComponent,
  UbidModalComponent,
} from 'app/modules/inventory/actions'
import type { InventoryType, Profile } from '../../../inventory'
import {
  AuditTemplateExportModalComponent,
  AuditTemplateImportModalComponent,
  CopyToCycleModalComponent,
  EmailModalComponent,
  FempExportModalComponent,
  GeocodeModalComponent,
  MergeModalComponent,
  RefreshMetadataModalComponent,
  UbidCompareComponent,
  UbidDecodeComponent,
  UpdateDerivedDataComponent,
} from '../actions'

@Component({
  selector: 'seed-inventory-grid-actions',
  templateUrl: './actions.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MenuItemComponent, MaterialImports, TranslocoDirective],
})
export class ActionsComponent implements OnDestroy, OnChanges, OnInit {
  @Input() cycleId: number
  @Input() cycles: Cycle[] = []
  @Input() gridApi: GridApi
  @Input() groupMode = false
  @Input() inventory: Record<string, unknown>[]
  @Input() orgId: number
  @Input() profile: Profile
  @Input() profiles: Profile[]
  @Input() selectedStateIds: number[]
  @Input() selectedViewIds: number[]
  @Input() type: InventoryType
  @Output() refreshInventory = new EventEmitter<number | null>()
  @Output() selectedAll = new EventEmitter<void>()
  @Output() toggleAccessLevels = new EventEmitter<void>()
  private _auditTemplateService = inject(AuditTemplateService)
  private _inventoryService = inject(InventoryService)
  private _organizationService = inject(OrganizationService)
  private _dialog = inject(MatDialog)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  hasSelection: boolean
  organization: Organization | null = null
  showAccessLevelInstances = true

  get canEmailSelection(): boolean {
    return this.hasSelection && this.selectedStateIds.length === this.selectedViewIds.length
  }

  ngOnInit(): void {
    this._organizationService.currentOrganization$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((org) => {
      this.organization = org
    })
  }

  baseData() {
    return {
      orgId: this.orgId,
      type: this.type,
      viewIds: this.selectedViewIds,
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.selectedViewIds) {
      this.hasSelection = this.selectedViewIds.length > 0
    }
  }

  openAuditTemplateExportModal() {
    const dialogRef = this._dialog.open(AuditTemplateExportModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, viewIds: this.selectedViewIds },
    })
    this.afterClosed(dialogRef)
  }

  openAuditTemplateImportModal() {
    const dialogRef = this._dialog.open(AuditTemplateImportModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, viewIds: this.selectedViewIds, org: this.organization, cycles: this.cycles },
    })
    this.afterClosed(dialogRef)
  }

  updateSalesforce() {
    this._inventoryService
      .updateSalesforce(this.orgId, this.selectedViewIds)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((result) => {
        if (result.status === 'success') {
          this._snackBar.success(result.message || 'Salesforce updated successfully.')
          this.refreshInventory.emit(null)
        } else {
          this._snackBar.alert(result.message || 'Error updating Salesforce.')
        }
      })
  }

  toggleAccessLevelInstances() {
    this.showAccessLevelInstances = !this.showAccessLevelInstances
    this.toggleAccessLevels.emit()
  }

  // The parent fetches every matching id so filters, labels, and groups are respected
  selectAll() {
    this.selectedAll.emit()
  }

  deselectAll() {
    this.gridApi.deselectAll()
  }

  deleteStates = () => {
    const displayType = this.type === 'taxlots' ? 'Tax Lot' : 'Property'
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: `${this.selectedViewIds.length} ${displayType} States`, instance: '' },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        switchMap(() => {
          return this.type === 'taxlots'
            ? this._inventoryService.deleteTaxlotStates({ orgId: this.orgId, viewIds: this.selectedViewIds })
            : this._inventoryService.deletePropertyStates({ orgId: this.orgId, viewIds: this.selectedViewIds })
        }),
        tap(() => {
          this.refreshInventory.emit()
        }),
      )
      .subscribe()
  }

  openExportModal() {
    const dialogRef = this._dialog.open(ExportModalComponent, {
      width: '40rem',
      data: { ...this.baseData(), profileId: this.profile?.id || null },
    })
    this.afterClosed(dialogRef)
  }

  openMergeModal() {
    const dialogRef = this._dialog.open(MergeModalComponent, {
      width: '50rem',
      data: { ...this.baseData(), cycleId: this.cycleId, profileId: this.profile?.id || null },
    })
    this.afterClosed(dialogRef)
  }

  openCopyToCycleModal() {
    const dialogRef = this._dialog.open(CopyToCycleModalComponent, {
      width: '40rem',
      data: { ...this.baseData(), cycles: this.cycles, profiles: this.profiles, currentCycleId: this.cycleId },
    })
    this.afterClosed(dialogRef)
  }

  openShowPopulatedColumnsModal() {
    const dialogRef = this._dialog.open(ModalComponent, {
      width: '40rem',
      data: {
        columns: [],
        cycleId: this.cycleId,
        inventoryType: this.type,
        location: 'List View Profile',
        mode: 'populate',
        orgId: this.orgId,
        profile: this.profile,
        profiles: this.profiles,
        type: this.type === 'taxlots' ? 'Tax Lot' : 'Property',
      },
    })

    this.afterClosed(dialogRef)
  }

  openAliChangeModal() {
    const dialogRef = this._dialog.open(AliChangeModalComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openAnalysisRunModal() {
    const dialogRef = this._dialog.open(AnalysisRunModalComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openDataQualityCheck() {
    const dialogRef = this._dialog.open(DQCStartModalComponent, {
      width: '40rem',
      disableClose: true,
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openDerivedDataUpdateModal() {
    const dialogRef = this._dialog.open(UpdateDerivedDataComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openGroupsModal() {
    const dialogRef = this._dialog.open(GroupsModalComponent, {
      width: '50rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openLabelsModal() {
    const dialogRef = this._dialog.open(LabelsModalComponent, {
      width: '50rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openRefreshMetadataModal() {
    const dialogRef = this._dialog.open(RefreshMetadataModalComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openEmailModal() {
    if (!this.canEmailSelection) return

    const dialogRef = this._dialog.open(EmailModalComponent, {
      width: '40rem',
      data: {
        orgId: this.orgId,
        stateIds: this.selectedStateIds,
        type: this.type,
      },
    })
    this.afterClosed(dialogRef)
  }

  openFempExportModal() {
    const dialogRef = this._dialog.open(FempExportModalComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openGeocodeModal() {
    const dialogRef = this._dialog.open(GeocodeModalComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openUbidModal() {
    const dialogRef = this._dialog.open(UbidModalComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openUbidCompareModal() {
    const dialogRef = this._dialog.open(UbidCompareComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  openUbidDecodeModal() {
    const dialogRef = this._dialog.open(UbidDecodeComponent, {
      width: '40rem',
      data: this.baseData(),
    })
    this.afterClosed(dialogRef)
  }

  afterClosed(dialogRef: MatDialogRef<unknown>) {
    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        tap((result) => {
          this.refreshInventory.emit(typeof result === 'number' ? result : null)
        }),
      )
      .subscribe()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
