import type { AfterViewInit, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import type { MatDrawer } from '@angular/material/sidenav'
import { ActivatedRoute, RouterOutlet } from '@angular/router'
import { filter, forkJoin, switchMap, tap } from 'rxjs'
import { InventoryService, UbidService, UserService } from '@seed/api'
import type { NavigationItem } from '@seed/components'
import { DrawerService, VerticalNavigationComponent } from '@seed/components'
import { ScrollResetDirective } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from '../inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-layout',
  templateUrl: './detail-layout.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, RouterOutlet, ScrollResetDirective, VerticalNavigationComponent],
})
export class DetailLayoutComponent implements AfterViewInit, OnInit {
  @ViewChild('drawer') drawer!: MatDrawer
  private _drawerService = inject(DrawerService)
  private _activatedRoute = inject(ActivatedRoute)
  private _userService = inject(UserService)
  private _ubidService = inject(UbidService)
  private _inventoryService = inject(InventoryService)
  viewId = parseInt(this._activatedRoute.snapshot.paramMap.get('id'))
  type = this._activatedRoute.snapshot.paramMap.get('type') as InventoryType
  orgId: number
  displayName = this.type === 'taxlots' ? 'Tax Lot' : 'Property'

  analyses: NavigationItem = {
    id: `properties/${this.viewId}}/analyses`,
    link: `/properties/${this.viewId}/analyses`,
    exactMatch: true,
    title: 'Analyses',
    type: 'basic',
  }

  detail: NavigationItem = {
    id: `${this.type}/${this.viewId}}/`,
    link: `/${this.type}/${this.viewId}/`,
    exactMatch: true,
    title: 'Detail',
    type: 'basic',
  }

  columnDetailProfiles: NavigationItem = {
    id: `${this.type}/${this.viewId}/column-detail-profiles`,
    link: `/${this.type}/${this.viewId}/column-detail-profiles`,
    title: 'Column Detail Profiles',
    type: 'basic',
  }

  crossCycles: NavigationItem = {
    id: `${this.type}/${this.viewId}/cross-cycles`,
    link: `/${this.type}/${this.viewId}/cross-cycles`,
    title: 'Cross Cycles',
    type: 'basic',
  }

  meters: NavigationItem = {
    id: `properties/${this.viewId}}/meters`,
    link: `/properties/${this.viewId}/meters`,
    exactMatch: true,
    title: 'Meters',
    type: 'basic',
  }

  notes: NavigationItem = {
    id: `${this.type}/${this.viewId}/notes`,
    link: `/${this.type}/${this.viewId}/notes`,
    title: 'Notes',
    type: 'basic',
  }

  sensors: NavigationItem = {
    id: `properties/${this.viewId}}/sensors`,
    link: `/properties/${this.viewId}/sensors`,
    exactMatch: true,
    title: 'Sensors',
    type: 'basic',
  }

  timeline: NavigationItem = {
    id: `properties/${this.viewId}}/timeline`,
    link: `/properties/${this.viewId}/timeline`,
    exactMatch: true,
    title: 'Timeline',
    type: 'basic',
  }

  ubids: NavigationItem = {
    id: `${this.type}/${this.viewId}}/ubids`,
    link: `/${this.type}/${this.viewId}/ubids`,
    exactMatch: true,
    title: 'UBIDs',
    type: 'basic',
  }

  propertyChildren: NavigationItem[] = [
    this.detail,
    this.analyses,
    this.columnDetailProfiles,
    this.crossCycles,
    this.meters,
    this.notes,
    this.sensors,
    this.timeline,
    this.ubids,
  ]

  taxlotChildren: NavigationItem[] = [this.detail, this.columnDetailProfiles, this.crossCycles, this.notes, this.ubids]

  readonly detailNavigationMenu: NavigationItem[] = [
    {
      id: `${this.type}/detail`,
      title: this.displayName,
      type: 'group',
      children: this.type === 'taxlots' ? this.taxlotChildren : this.propertyChildren,
    },
  ]

  ngOnInit() {
    this.initStreams()
  }

  initStreams() {
    this._userService.currentOrganizationId$
      .pipe(
        tap((orgId) => {
          this.orgId = orgId
        }),
        // endpoints that return observables and initiate streams
        filter(() => Boolean(this.orgId && this.viewId && this.type)),
        switchMap(() => forkJoin([this._inventoryService.getView(this.orgId, this.viewId, this.type)])),
        // endpoints that initiate streams
        tap(() => {
          this._ubidService.list(this.orgId, this.viewId, this.type)
        }),
      )
      .subscribe()
  }

  ngAfterViewInit() {
    this._drawerService.setDrawer(this.drawer)
  }
}
