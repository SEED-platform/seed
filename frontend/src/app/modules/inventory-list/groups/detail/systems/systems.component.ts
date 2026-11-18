import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { MatTooltipModule } from '@angular/material/tooltip'
import { ActivatedRoute, Router } from '@angular/router'
import { filter, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { GroupService, GroupSystem } from '@seed/api'
import { GroupsService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { GroupDetailLayoutComponent } from '../group-detail-layout.component'
import type { ServiceDialogData, SystemDialogData } from './dialog-types'
import { ServiceDialogComponent } from './service-dialog/service-dialog.component'
import { SystemDialogComponent } from './system-dialog/system-dialog.component'

@Component({
  selector: 'seed-group-systems',
  templateUrl: './systems.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, MatTooltipModule, PageComponent],
})
export class GroupSystemsComponent implements OnDestroy, OnInit {
  private _groupsService = inject(GroupsService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private _dialog = inject(MatDialog)
  private _router = inject(Router)
  private readonly _unsubscribeAll$ = new Subject<void>()

  groupId = parseInt(this._route.parent.snapshot.paramMap.get('groupId'))
  layout = inject(GroupDetailLayoutComponent) // parent route component; supplies breadcrumb links
  orgId: number
  systemsByType: Record<string, GroupSystem[]> = {}
  systemTypeKeys: string[] = []
  expandedSystems = new Set<number>()
  loading = true

  ngOnInit() {
    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter((org) => Boolean(org?.org_id)),
        take(1),
        tap(({ org_id }) => {
          this.orgId = org_id
        }),
        switchMap(() => this.loadSystems()),
      )
      .subscribe()
  }

  loadSystems() {
    this.loading = true
    return this._groupsService.getSystemsByType(this.orgId, this.groupId).pipe(
      tap((data) => {
        this.systemsByType = data
        this.systemTypeKeys = Object.keys(data)
        this.loading = false
      }),
    )
  }

  createSystem() {
    const data: SystemDialogData = { action: 'create', orgId: this.orgId, groupId: this.groupId }
    this._dialog
      .open(SystemDialogComponent, { data, width: '500px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.loadSystems()),
      )
      .subscribe()
  }

  editSystem(system: GroupSystem) {
    const data: SystemDialogData = { action: 'edit', orgId: this.orgId, groupId: this.groupId, system }
    this._dialog
      .open(SystemDialogComponent, { data, width: '500px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.loadSystems()),
      )
      .subscribe()
  }

  deleteSystem(system: GroupSystem) {
    const data: SystemDialogData = { action: 'delete', orgId: this.orgId, groupId: this.groupId, system }
    this._dialog
      .open(SystemDialogComponent, { data, width: '400px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.loadSystems()),
      )
      .subscribe()
  }

  createService(system: GroupSystem) {
    const data: ServiceDialogData = {
      action: 'create',
      orgId: this.orgId,
      groupId: this.groupId,
      systemId: system.id,
      systemName: system.name,
    }
    this._dialog
      .open(ServiceDialogComponent, { data, width: '450px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.loadSystems()),
      )
      .subscribe()
  }

  editService(system: GroupSystem, service: GroupService) {
    const data: ServiceDialogData = {
      action: 'edit',
      orgId: this.orgId,
      groupId: this.groupId,
      systemId: system.id,
      systemName: system.name,
      service,
    }
    this._dialog
      .open(ServiceDialogComponent, { data, width: '450px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.loadSystems()),
      )
      .subscribe()
  }

  deleteService(system: GroupSystem, service: GroupService) {
    const data: ServiceDialogData = {
      action: 'delete',
      orgId: this.orgId,
      groupId: this.groupId,
      systemId: system.id,
      systemName: system.name,
      service,
    }
    this._dialog
      .open(ServiceDialogComponent, { data, width: '400px' })
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.loadSystems()),
      )
      .subscribe()
  }

  toggleServices(systemId: number) {
    if (this.expandedSystems.has(systemId)) {
      this.expandedSystems.delete(systemId)
    } else {
      this.expandedSystems.add(systemId)
    }
  }

  getColspan(typeKey: string): number {
    const base = this.getBaseType(typeKey)
    // +1 for the expand/collapse column
    const colMap: Record<string, number> = { DES: 7, EVSE: 7, Battery: 7, 'Aggregate Meter': 4 }
    return colMap[base] ?? 4
  }

  getBaseType(typeKey: string): string {
    if (typeKey.startsWith('DES')) return 'DES'
    if (typeKey.startsWith('EVSE')) return 'EVSE'
    if (typeKey.startsWith('Battery')) return 'Battery'
    if (typeKey.startsWith('Aggregate Meter')) return 'Aggregate Meter'
    return typeKey
  }

  viewServiceDetail(system: GroupSystem, service: GroupService) {
    void this._router.navigate(['services', system.id, service.id], { relativeTo: this._route })
  }

  ngOnDestroy() {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
