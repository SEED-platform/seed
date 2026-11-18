import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute, RouterLink } from '@angular/router'
import { filter, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { GroupServiceDetail } from '@seed/api'
import { GroupsService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from 'app/modules/inventory/inventory.types'
import { GroupDetailLayoutComponent } from '../../group-detail-layout.component'
import type { AddPropertiesDialogData } from './dialogs/add-properties-dialog.component'
import { AddPropertiesDialogComponent } from './dialogs/add-properties-dialog.component'

@Component({
  selector: 'seed-service-detail',
  templateUrl: './service-detail.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, PageComponent, RouterLink],
})
export class ServiceDetailComponent implements OnDestroy, OnInit {
  private _dialog = inject(MatDialog)
  private _groupsService = inject(GroupsService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private readonly _unsubscribeAll$ = new Subject<void>()

  groupId: number
  layout = inject(GroupDetailLayoutComponent) // parent route component; supplies breadcrumb links
  systemId: number
  serviceId: number
  orgId: number
  inventoryType: InventoryType
  service: GroupServiceDetail | null = null
  loading = true

  ngOnInit() {
    this.systemId = parseInt(this._route.snapshot.paramMap.get('systemId'))
    this.serviceId = parseInt(this._route.snapshot.paramMap.get('serviceId'))

    // Walk up to find groupId and type from parent routes using pathFromRoot
    for (const route of this._route.pathFromRoot) {
      if (!this.groupId) {
        const gid = route.snapshot.paramMap.get('groupId')
        if (gid) {
          this.groupId = parseInt(gid)
        }
      }
      if (!this.inventoryType) {
        const type = route.snapshot.paramMap.get('type')
        if (type) {
          this.inventoryType = type as InventoryType
        }
      }
    }

    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter((org) => Boolean(org?.org_id)),
        take(1),
        tap(({ org_id }) => {
          this.orgId = org_id
        }),
        switchMap(() => this.loadService()),
      )
      .subscribe()
  }

  loadService() {
    this.loading = true
    return this._groupsService.getServiceDetail(this.orgId, this.groupId, this.systemId, this.serviceId).pipe(
      tap((data) => {
        this.service = data
        this.loading = false
      }),
    )
  }

  addProperties() {
    const data: AddPropertiesDialogData = {
      orgId: this.orgId,
      groupId: this.groupId,
      systemId: this.systemId,
      serviceId: this.serviceId,
    }
    this._dialog
      .open(AddPropertiesDialogComponent, { data, width: '500px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.loadService()),
      )
      .subscribe()
  }

  ngOnDestroy() {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
