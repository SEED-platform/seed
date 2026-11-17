import { CommonModule, Location } from '@angular/common'
import type { AfterViewInit, OnInit, Type } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import type { MatDrawer } from '@angular/material/sidenav'
import { Title } from '@angular/platform-browser'
import { Router, RouterOutlet } from '@angular/router'
import { DrawerService, InventoryTabComponent, type NavigationItem, VerticalNavigationComponent } from '@seed/components'
import { PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from 'app/modules/inventory'
import { ColumnDataTypesHelpComponent } from './data-types/help.component'
import { ColumnGeocodingHelpComponent } from './geocoding/help.component'
import { ColumnImportSettingsHelpComponent } from './import-settings/help.component'
import { ColumnListHelpComponent } from './list/help.component'
import { ColumnMappingHelpComponent } from './mappings/help.component'
import { ColumnMatchingCriteriaHelpComponent } from './matching-criteria/help.component'

type ColumnNavigationItem = NavigationItem & { useTabs: boolean; helpComponent: Type<Component> | null }
@Component({
  selector: 'seed-organizations-columns',
  templateUrl: './columns.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, SharedImports, InventoryTabComponent, MaterialImports, PageComponent, VerticalNavigationComponent, RouterOutlet],
})
export class ColumnsComponent implements AfterViewInit, OnInit {
  @ViewChild('drawer') drawer!: MatDrawer
  private _drawerService = inject(DrawerService)
  private _title = inject(Title)
  private _router = inject(Router)
  private _location = inject(Location)
  drawerOpened = true
  helpOpened = false
  helpComponent: Type<Component> | null
  tabs = [
    {
      label: 'Properties',
      route: 'properties',
    },
    {
      label: 'TaxLots',
      route: 'taxlots',
    },
  ]
  pageTitle: string
  useTabs = false
  columnsNavigationMenu: ColumnNavigationItem[] = [
    {
      id: 'organizations/columns/list',
      exactMatch: false,
      title: 'Column List',
      link: '/organizations/columns/list',
      type: 'basic',
      useTabs: true,
      fn: (n: ColumnNavigationItem) => {
        this.setPageInfo(n)
      },
      helpComponent: ColumnListHelpComponent,
    },
    {
      id: 'organizations/columns/geocoding',
      link: '/organizations/columns/geocoding',
      title: 'Geocoding',
      type: 'basic',
      useTabs: true,
      fn: (n: ColumnNavigationItem) => {
        this.setPageInfo(n)
      },
      helpComponent: ColumnGeocodingHelpComponent,
    },
    {
      id: 'organization/columns/data-type',
      link: '/organizations/columns/data-types',
      title: 'Data Types',
      type: 'basic',
      useTabs: true,
      fn: (n: ColumnNavigationItem) => {
        this.setPageInfo(n)
      },
      helpComponent: ColumnDataTypesHelpComponent,
    },
    {
      id: 'organizations/columns/import-settings',
      link: '/organizations/columns/import-settings',
      title: 'Import Settings',
      type: 'basic',
      useTabs: true,
      fn: (n: ColumnNavigationItem) => {
        this.setPageInfo(n)
      },
      helpComponent: ColumnImportSettingsHelpComponent,
    },
    {
      id: 'organizations/columns/matching-criteria',
      link: '/organizations/columns/matching-criteria',
      title: 'Matching Criteria',
      type: 'basic',
      useTabs: true,
      fn: (n: ColumnNavigationItem) => {
        this.setPageInfo(n)
      },
      helpComponent: ColumnMatchingCriteriaHelpComponent,
    },
    {
      id: 'organizations/columns/mappings',
      link: '/organizations/columns/mappings',
      title: 'Column Mappings',
      type: 'basic',
      useTabs: false,
      fn: (n: ColumnNavigationItem) => {
        this.setPageInfo(n)
      },
      helpComponent: ColumnMappingHelpComponent,
    },
  ]

  ngOnInit(): void {
    this.setTitle()
  }

  ngAfterViewInit() {
    this._drawerService.setDrawer(this.drawer)
  }

  currentType() {
    return this._location.path().split('/').pop() as InventoryType
  }

  async navigateTo(type: InventoryType) {
    const loc = this._location.path()
    if (loc.includes(type)) return

    const newPath = loc.replace(this.inverseType(type), type)
    await this._router.navigateByUrl(newPath).then(() => {
      this.setTitle()
    })
  }

  inverseType(type: string): string {
    return type === 'properties' ? 'taxlots' : 'properties'
  }

  setPageInfo(n?: ColumnNavigationItem) {
    // No matching child route (e.g. mid-redirect): fall back to the generic section title
    this.pageTitle = n?.title ?? 'Columns'
    this.useTabs = n?.useTabs ?? false
    this.helpComponent = n?.helpComponent ?? null
  }

  setTitle() {
    let basePath = this._location.path()
    if (basePath.includes('properties')) {
      basePath = `${this._location.path().split('/').slice(0, -1).join('/')}/properties`
    }
    this.setPageInfo(this.columnsNavigationMenu.find((n) => basePath.includes(n.link)))
  }

  toggleDrawer = (): void => {
    this.drawerOpened = !this.drawerOpened
    if (this.drawerOpened) {
      this.helpOpened = false
    }
  }

  toggleHelp = () => {
    this.helpOpened = !this.helpOpened
  }
}
