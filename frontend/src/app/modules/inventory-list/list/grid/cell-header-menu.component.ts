import type { FlexibleConnectedPositionStrategyOrigin, OverlayRef } from '@angular/cdk/overlay'
import { Overlay } from '@angular/cdk/overlay'
import { TemplatePortal } from '@angular/cdk/portal'
import type { AfterViewInit, OnDestroy, TemplateRef } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild, ViewContainerRef } from '@angular/core'
import { TranslocoDirective } from '@jsverse/transloco'
import type { IHeaderAngularComp } from 'ag-grid-angular'
import type { Column, GridApi, IHeaderParams } from 'ag-grid-community'
import { take } from 'rxjs'
import type { CurrentUser, OrganizationUserSettings } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-grid-cell-header-menu',
  templateUrl: './cell-header-menu.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, TranslocoDirective],
})
export class CellHeaderMenuComponent implements IHeaderAngularComp, AfterViewInit, OnDestroy {
  @ViewChild('menu') menuTemplate!: TemplateRef<unknown>
  @ViewChild('trigger') trigger!: FlexibleConnectedPositionStrategyOrigin

  private _configService = inject(ConfigService)
  private _organizationService = inject(OrganizationService)
  private _overlay = inject(Overlay)
  private _vcr = inject(ViewContainerRef)
  column: Column<unknown>
  gridApi: GridApi
  opened = false
  orgId: number
  orgUserId: number
  overlayRef: OverlayRef
  params: IHeaderParams
  pinState: unknown
  scheme: 'dark' | 'light'
  sortIcon = ''
  type: InventoryType
  userSettings: OrganizationUserSettings
  private _openedWithKeyboard = false

  agInit(params: IHeaderParams & { currentUser: CurrentUser; type: InventoryType }): void {
    this.params = params
    this.column = params.column
    this.gridApi = params.api
    this.type = params.type
    const { org_id, org_user_id, settings } = params.currentUser
    this.orgId = org_id
    this.orgUserId = org_user_id
    this.userSettings = settings
    // ag-grid owns header focus, so listen on the header cell itself for the menu shortcut
    params.eGridHeader.addEventListener('keydown', this._onHeaderKeyDown)
    params.eGridHeader.setAttribute('aria-keyshortcuts', 'Alt+ArrowDown')
  }

  get isOpen(): boolean {
    return this.overlayRef?.hasAttached() ?? false
  }

  ngAfterViewInit(): void {
    this.getScheme()
    this.setOverlay()
    this.updateSortState()
    this.pinState = this.column.isPinned()
    this.column.addEventListener('sortChanged', () => {
      this.updateSortState()
    })
    this.gridApi.addEventListener('columnPinned', () => {
      this.pinState = this.column.isPinned()
    })
  }

  getScheme() {
    this._configService.scheme$.subscribe((scheme) => {
      this.scheme = scheme
    })
  }

  updateSortState() {
    const state = this.gridApi.getColumnState().find((col) => col.colId === this.params.column.getColId())
    const sortDir = state?.sort ?? null
    const iconMap = {
      asc: 'fa-solid:arrow-up',
      desc: 'fa-solid:arrow-down',
    }
    this.sortIcon = iconMap[sortDir] ?? ''
  }

  setOverlay() {
    const positionStrategy = this._overlay
      .position()
      .flexibleConnectedTo(this.trigger)
      .withPositions([
        {
          originX: 'end',
          originY: 'bottom',
          overlayX: 'start',
          overlayY: 'top',
        },
      ])

    this.overlayRef = this._overlay.create({
      positionStrategy,
      hasBackdrop: true,
      backdropClass: 'transparent-backdrop',
    })

    this.overlayRef.backdropClick().subscribe(() => {
      this.overlayRef.detach()
    })
  }

  ngOnDestroy(): void {
    this.params?.eGridHeader.removeEventListener('keydown', this._onHeaderKeyDown)
    this.overlayRef?.dispose()
  }

  toggleMenu({ viaKeyboard = false }: { viaKeyboard?: boolean } = {}): void {
    // event.stopPropagation()
    // this.menuVisible = !this.menuVisible
    this._openedWithKeyboard = viaKeyboard
    if (this.overlayRef?.hasAttached()) {
      this.overlayRef.detach()
    } else {
      const portal = new TemplatePortal(this.menuTemplate, this._vcr)
      this.overlayRef?.attach(portal)
      this._menuItems()[0]?.focus()
    }
  }

  // Arrow keys move between items, Escape/Tab close the menu and return focus to the column header
  onMenuKeyDown(event: KeyboardEvent): void {
    const items = this._menuItems()
    const current = items.indexOf(document.activeElement as HTMLButtonElement)

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const step = event.key === 'ArrowDown' ? 1 : -1
      items[(current + step + items.length) % items.length]?.focus()
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault()
      items[event.key === 'Home' ? 0 : items.length - 1]?.focus()
    } else if (event.key === 'Escape' || event.key === 'Tab') {
      event.preventDefault()
      this.detach()
    }
  }

  sortCol(direction: 'asc' | 'desc' | null): void {
    this.gridApi.applyColumnState({
      state: [{ colId: this.params.column.getColId(), sort: direction }],
      defaultState: { sort: null },
    })
    const dir = direction === 'desc' ? '-' : ''
    const colDef = this.column.getColDef()
    const sort = `${dir}${colDef.field}`
    this.userSettings.sorts?.[this.type].push(sort)

    this.detach()
  }

  pinCol(direction: 'left' | 'right' | null): void {
    this.gridApi.setColumnsPinned([this.column], direction)
    this.detach()
    this.updatePins(direction)
  }

  updatePins(direction: 'left' | 'right'): void {
    const field = this.column.getColDef().field
    const pins = this.userSettings.pins[this.type]
    const left = new Set(pins.left)
    const right = new Set(pins.right)

    // Clear from both sides
    left.delete(field)
    right.delete(field)

    if (direction === 'left') left.add(field)
    if (direction === 'right') right.add(field)

    // Assign back as arrays
    pins.left = Array.from(left)
    pins.right = Array.from(right)

    this.updateOrgUserSettings()
  }

  hideCol() {
    this.gridApi.setColumnsVisible([this.column], false)
    this.detach()
  }

  updateOrgUserSettings() {
    return this._organizationService.updateOrganizationUser(this.orgUserId, this.orgId, this.userSettings).pipe(take(1)).subscribe()
  }

  detach() {
    const restoreFocus = this._openedWithKeyboard || this.overlayRef.overlayElement.contains(document.activeElement)
    this.overlayRef.detach()
    if (restoreFocus) {
      this.params.eGridHeader.focus()
    }
  }

  refresh() {
    return true
  }

  private _onHeaderKeyDown = (event: KeyboardEvent) => {
    if (event.altKey && event.key === 'ArrowDown') {
      event.preventDefault()
      event.stopPropagation()
      this.toggleMenu({ viaKeyboard: true })
    }
  }

  private _menuItems(): HTMLButtonElement[] {
    return Array.from(this.overlayRef?.overlayElement.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? [])
  }
}
