import type { AfterViewInit, OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import type { MatDrawer } from '@angular/material/sidenav'
import { ActivatedRoute, RouterOutlet } from '@angular/router'
import { filter, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { InventoryGroup } from '@seed/api'
import { GroupsService, OrganizationService } from '@seed/api'
import type { NavigationItem } from '@seed/components'
import { DrawerService, VerticalNavigationComponent } from '@seed/components'
import { ScrollResetDirective } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-group-detail-layout',
  templateUrl: './group-detail-layout.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, RouterOutlet, ScrollResetDirective, VerticalNavigationComponent],
})
export class GroupDetailLayoutComponent implements AfterViewInit, OnDestroy, OnInit {
  @ViewChild('drawer') drawer!: MatDrawer
  private _drawerService = inject(DrawerService)
  private _activatedRoute = inject(ActivatedRoute)
  private _groupsService = inject(GroupsService)
  private _organizationService = inject(OrganizationService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  groupId = parseInt(this._activatedRoute.snapshot.paramMap.get('groupId'))
  type = this._activatedRoute.snapshot.paramMap.get('type') as InventoryType
  orgId: number
  group: InventoryGroup

  navigationMenu: NavigationItem[] = []

  // Used by the child pages' breadcrumbs
  get groupsLink(): string {
    return `/${this.type}/groups`
  }

  get groupLink(): string {
    return `${this.groupsLink}/${this.groupId}`
  }

  ngOnInit() {
    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter((org) => Boolean(org?.org_id)),
        take(1),
        tap(({ org_id }) => {
          this.orgId = org_id
        }),
        switchMap(() => this._groupsService.getById(this.orgId, this.groupId)),
        tap((group) => {
          this.group = group
          this.buildNavigation()
        }),
      )
      .subscribe()
  }

  buildNavigation() {
    const base = `/${this.type}/groups/${this.groupId}`
    this.navigationMenu = [
      {
        id: 'group-detail',
        title: this.group?.name ?? 'Group',
        type: 'group',
        children: [
          { id: 'dashboard', link: `${base}/dashboard`, title: 'Dashboard', type: 'basic', exactMatch: true },
          { id: 'properties', link: `${base}/properties`, title: 'Properties', type: 'basic' },
          { id: 'systems', link: `${base}/systems`, title: 'Systems & Services', type: 'basic' },
          { id: 'meters', link: `${base}/meters`, title: 'Meters', type: 'basic' },
          { id: 'map', link: `${base}/map`, title: 'Map', type: 'basic' },
        ],
      },
    ]
  }

  ngAfterViewInit() {
    this._drawerService.setDrawer(this.drawer)
  }

  ngOnDestroy() {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
