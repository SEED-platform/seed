import { CommonModule } from '@angular/common'
import type { OnChanges, OnInit, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { type MatSelect } from '@angular/material/select'
import { Router } from '@angular/router'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import { filter, take, tap } from 'rxjs'
import type { AccessLevelInstance, Cycle, Label, Organization } from '@seed/api'
import { AuditTemplateService, CycleService, ConfigService as DeploymentConfigService, InventoryService } from '@seed/api'
import { LabelComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService, ConfirmationService } from '@seed/services'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import { AnalysisRunModalComponent, GroupsModalComponent, LabelsModalComponent, UbidModalComponent } from 'app/modules/inventory/actions'
import type { GenericView, GroupMapping, Profile, ViewResponse } from 'app/modules/inventory/inventory.types'
import { AuditTemplateExportModalComponent, AuditTemplateImportModalComponent } from 'app/modules/inventory-list/list/actions'
import { ModalComponent } from '../../column-list-profile/modal/modal.component'
import { MapComponent } from './map.component'
import { ExportBuildingSyncModalComponent } from './modal/export-building-sync-modal.component'
import { ExportBuildingSyncXlsxModalComponent } from './modal/export-building-sync-xlsx-modal.component'
import { UpdateWithBuildingSyncModalComponent } from './modal/update-with-building-sync-modal.component'
import { UpdateWithEspmModalComponent } from './modal/update-with-espm-modal.component'

@Component({
  selector: 'seed-inventory-detail-header',
  templateUrl: './header.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, CommonModule, LabelComponent, MapComponent, MaterialImports],
})
export class HeaderComponent implements OnInit, OnChanges {
  @Input() currentProfile: Profile
  @Input() labels: Label[]
  @Input() org: Organization
  @Input() profiles: Profile[]
  @Input() selectedView: GenericView
  @Input() view: ViewResponse
  @Input() views: GenericView[]
  @Input() type: 'properties' | 'taxlots'
  @Output() changeProfile = new EventEmitter<number>()
  @Output() changeView = new EventEmitter<number>()
  @Output() refreshDetail = new EventEmitter<null>()
  private _configService = inject(ConfigService)
  private _deploymentConfigService = inject(DeploymentConfigService)
  private _confirmationService = inject(ConfirmationService)
  private _auditTemplateService = inject(AuditTemplateService)
  private _cycleService = inject(CycleService)
  private _dialog = inject(MatDialog)
  private _inventoryService = inject(InventoryService)
  private _router = inject(Router)
  private _snackBar = inject(SnackBarService)
  get groupMappings(): GroupMapping[] {
    return this.view?.property?.group_mappings ?? []
  }

  get shownLabels(): Label[] {
    return this.labels?.filter((label) => label.show_in_list) ?? []
  }
  accessLevelInstance: AccessLevelInstance
  aliDataSource = []
  aliColumns: string[] = []
  aliColumnDefs: ColDef[] = []
  aliRowData: Record<string, unknown>[] = []
  enableMap: boolean
  gridApi: GridApi
  gridTheme$ = this._configService.gridTheme$
  actions: { name: string; action: () => void; disabled: boolean }[] = []
  salesforceEnabled = true

  ngOnInit(): void {
    this._deploymentConfigService.config$.subscribe(({ integrations }) => {
      this.salesforceEnabled = integrations.salesforce
      this.buildActions()
    })
    this.enableMap = Boolean(this.view.state.ubid && this.view.state.bounding_box && this.view.state.centroid)
    this.setAliGrid()
    this.buildActions()
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.org || changes.type || changes.view) {
      this.enableMap = Boolean(this.view?.state.ubid && this.view?.state.bounding_box && this.view?.state.centroid)
      this.buildActions()
    }
  }

  buildActions(): void {
    const isProperties = this.type === 'properties'
    this.actions = [
      {
        name: 'Add to/Remove from Groups',
        action: () => {
          this.openGroupsModal()
        },
        disabled: false,
      },
      {
        name: 'Add/Remove Labels',
        action: () => {
          this.openLabelsModal()
        },
        disabled: false,
      },
      {
        name: 'Add/Update UBID',
        action: () => {
          this.openUbidModal()
        },
        disabled: false,
      },
      {
        name: 'Export Audit Template File (XML)',
        action: this.exportAuditTemplateXml.bind(this) as () => void,
        disabled: !isProperties,
      },
      {
        name: 'Export BuildingSync',
        action: () => {
          this.openExportBuildingSyncModal()
        },
        disabled: !isProperties,
      },
      {
        name: 'Export BuildingSync (Excel)',
        action: () => {
          this.openExportBuildingSyncXlsxModal()
        },
        disabled: !isProperties,
      },
      {
        name: 'Export to Audit Template',
        action: () => {
          this.openAuditTemplateExportModal()
        },
        disabled: !isProperties || !this.org?.audit_template_user,
      },
      {
        name: 'Merge and Link Matches',
        action: () => {
          this.openMergeAndLinkConfirmation()
        },
        disabled: false,
      },
      {
        name: 'Only Show Populated Columns',
        action: () => {
          this.openShowPopulatedColumnsModal()
        },
        disabled: false,
      },
      {
        name: 'Run Analysis',
        action: () => {
          this.openRunAnalysisModal()
        },
        disabled: !isProperties,
      },
      {
        name: 'Update with Audit Template',
        action: () => {
          this.openAuditTemplateImportModal()
        },
        disabled: !isProperties || !this.org?.audit_template_user || !this.org?.audit_template_sync_enabled,
      },
      {
        name: 'Update with BuildingSync',
        action: () => {
          this.openUpdateWithBuildingSyncModal()
        },
        disabled: !isProperties,
      },
      {
        name: 'Update with ESPM',
        action: () => {
          this.openUpdateWithEspmModal()
        },
        disabled: !isProperties,
      },
      ...(this.view?.history?.length > 1
        ? [
            {
              name: 'Unmerge Last',
              action: () => {
                this.openUnmergeConfirmation()
              },
              disabled: false,
            },
          ]
        : []),
      ...(this.salesforceEnabled && this.org?.bb_salesforce_enabled && isProperties
        ? [
            {
              name: 'Update Salesforce',
              action: () => {
                this.updateSalesforce()
              },
              disabled: false,
            },
          ]
        : []),
    ]
  }

  setAliGrid() {
    const inventoryKey = this.type === 'properties' ? 'property' : 'taxlot'

    // column defs (minus root level)
    for (const name of this.org.access_level_names.slice(1)) {
      this.aliColumnDefs.push({
        headerName: name,
        field: name,
        sortable: false,
        filter: false,
        resizable: true,
        suppressMovable: true,
        width: 100,
      })
    }
    // row data
    this.aliRowData.push(this.view[inventoryKey].access_level_instance.path)
  }

  onGridReady(agGrid: GridReadyEvent) {
    this.gridApi = agGrid.api
    this.gridApi.sizeColumnsToFit()
  }

  tempAction() {
    console.log('temp action')
  }

  openLabelsModal(): void {
    const dialogRef = this._dialog.open(LabelsModalComponent, {
      width: '50rem',
      data: {
        orgId: this.org.id,
        type: this.type,
        viewIds: [this.selectedView.id],
        appliedLabelIds: this.labels.map((l) => l.id),
        goalLabelIds: this.labels.filter((l) => l.is_applied_by_goal?.includes(this.selectedView.id)).map((l) => l.id),
      },
    })
    this.afterClosed(dialogRef)
  }

  openGroupsModal(): void {
    const dialogRef = this._dialog.open(GroupsModalComponent, {
      width: '50rem',
      data: { orgId: this.org.id, type: this.type, viewIds: [this.selectedView.id] },
    })
    this.afterClosed(dialogRef)
  }

  openUbidModal(): void {
    const dialogRef = this._dialog.open(UbidModalComponent, {
      width: '40rem',
      data: { orgId: this.org.id, type: this.type, viewIds: [this.selectedView.id] },
    })
    this.afterClosed(dialogRef)
  }

  exportAuditTemplateXml(): void {
    this._auditTemplateService
      .exportBuildingSyncAtFile(this.org.id, this.selectedView.id)
      .pipe(take(1))
      .subscribe((xml) => {
        const blob = new Blob([xml], { type: 'application/xml;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `buildingsync_at_property_${this.selectedView.id}.xml`
        a.click()
        setTimeout(() => {
          URL.revokeObjectURL(url)
        }, 0)
      })
  }

  openAuditTemplateExportModal(): void {
    this._dialog.open(AuditTemplateExportModalComponent, {
      width: '40rem',
      data: { orgId: this.org.id, viewIds: [this.selectedView.id] },
    })
  }

  openAuditTemplateImportModal(): void {
    this._cycleService.cycles$.pipe(take(1)).subscribe((cycles: Cycle[]) => {
      this._dialog.open(AuditTemplateImportModalComponent, {
        width: '40rem',
        data: { orgId: this.org.id, viewIds: [this.selectedView.id], org: this.org, cycles },
      })
    })
  }

  openExportBuildingSyncModal(): void {
    this._dialog.open(ExportBuildingSyncModalComponent, {
      width: '40rem',
      data: { orgId: this.org.id, viewId: this.selectedView.id },
    })
  }

  openExportBuildingSyncXlsxModal(): void {
    this._dialog.open(ExportBuildingSyncXlsxModalComponent, {
      width: '40rem',
      data: { orgId: this.org.id, viewId: this.selectedView.id, profileId: this.currentProfile?.id ?? null },
    })
  }

  openUpdateWithBuildingSyncModal(): void {
    const dialogRef = this._dialog.open(UpdateWithBuildingSyncModalComponent, {
      width: '40rem',
      data: { orgId: this.org.id, viewId: this.selectedView.id, cycleId: this.view.cycle.id },
    })
    this.afterClosed(dialogRef)
  }

  openMergeAndLinkConfirmation(): void {
    const ref = this._confirmationService.open({
      title: 'Merge and Link Matches',
      message: 'This will merge duplicate records and link matching properties and tax lots. This action cannot be undone. Continue?',
      actions: { confirm: { label: 'Merge and Link', color: 'warn' }, cancel: { show: true, label: 'Cancel' } },
    })
    ref
      .afterClosed()
      .pipe(
        filter((r) => r === 'confirmed'),
        take(1),
      )
      .subscribe(() => {
        this._inventoryService
          .matchMergeLink(this.org.id, this.selectedView.id, this.type)
          .pipe(take(1))
          .subscribe({
            next: ({ view_id }) => {
              this._snackBar.success('Match, merge, and link complete.')
              if (view_id && view_id !== this.selectedView.id) {
                void this._router.navigate([`/${this.type}/${view_id}`])
              } else {
                this.refreshDetail.emit()
              }
            },
            error: () => undefined,
          })
      })
  }

  openUnmergeConfirmation(): void {
    const ref = this._confirmationService.open({
      title: 'Unmerge Last',
      message: `This will undo the most recent merge for this ${this.type === 'properties' ? 'property' : 'tax lot'}. Continue?`,
      actions: { confirm: { label: 'Unmerge', color: 'warn' }, cancel: { show: true, label: 'Cancel' } },
    })
    ref
      .afterClosed()
      .pipe(
        filter((r) => r === 'confirmed'),
        take(1),
      )
      .subscribe(() => {
        this._inventoryService
          .unmerge(this.org.id, this.selectedView.id, this.type)
          .pipe(take(1))
          .subscribe({
            next: ({ view_id }) => {
              this._snackBar.success('Unmerge complete.')
              if (view_id && view_id !== this.selectedView.id) {
                void this._router.navigate([`/${this.type}/${view_id}`])
              } else {
                this.refreshDetail.emit()
              }
            },
            error: () => undefined,
          })
      })
  }

  openUpdateWithEspmModal(): void {
    const pmPropertyId = ((this.view?.state as Record<string, unknown>)?.pm_property_id as string) ?? ''
    const dialogRef = this._dialog.open(UpdateWithEspmModalComponent, {
      width: '40rem',
      data: { orgId: this.org.id, viewId: this.selectedView.id, cycleId: this.view.cycle.id, pmPropertyId },
    })
    this.afterClosed(dialogRef)
  }

  updateSalesforce(): void {
    this._inventoryService
      .updateSalesforce(this.org.id, [this.selectedView.id])
      .pipe(take(1))
      .subscribe((result) => {
        if (result.status === 'success') {
          this._snackBar.success(result.message || 'Salesforce updated successfully.')
        } else {
          this._snackBar.alert(result.message || 'Error updating Salesforce.')
        }
      })
  }

  afterClosed(dialogRef: ReturnType<typeof this._dialog.open>): void {
    dialogRef
      .afterClosed()
      .pipe(
        take(1),
        filter(Boolean),
        tap(() => {
          this.refreshDetail.emit()
        }),
      )
      .subscribe()
  }

  onAction(action: () => void, select: MatSelect) {
    select.writeValue(null)
    setTimeout(() => {
      action()
    })
  }

  onChangeProfile(profileId: number) {
    this.changeProfile.emit(profileId)
  }

  onChangeView(viewId: number) {
    this.changeView.emit(viewId)
  }

  openShowPopulatedColumnsModal() {
    const dialogRef = this._dialog.open(ModalComponent, {
      width: '40rem',
      data: {
        columns: [],
        cycleId: this.view.cycle.id,
        inventoryType: this.type,
        location: 'Detail View Profile',
        mode: 'populate',
        orgId: this.org.id,
        profile: this.currentProfile,
        profiles: this.profiles,
        type: this.type === 'taxlots' ? 'Tax Lot' : 'Property',
      },
    })

    dialogRef
      .afterClosed()
      .pipe(
        take(1),
        filter(Boolean),
        tap(() => {
          this.refreshDetail.emit()
        }),
      )
      .subscribe()
  }

  openRunAnalysisModal() {
    const dialogRef = this._dialog.open(AnalysisRunModalComponent, {
      width: '40rem',
      data: {
        orgId: this.org.id,
        viewIds: [this.selectedView.id],
        analysesLink: `/${this.type}/${this.selectedView.id}/analyses`,
      },
    })

    dialogRef
      .afterClosed()
      .pipe(
        take(1),
        filter(Boolean),
        tap(() => {
          this.refreshDetail.emit()
        }),
      )
      .subscribe()
  }

  trackByFn(_index: number, { id }: AccessLevelInstance) {
    return id
  }
}
