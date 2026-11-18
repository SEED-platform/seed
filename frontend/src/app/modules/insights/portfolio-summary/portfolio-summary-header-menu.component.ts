import type { FlexibleConnectedPositionStrategyOrigin, OverlayRef } from '@angular/cdk/overlay'
import { Overlay } from '@angular/cdk/overlay'
import { TemplatePortal } from '@angular/cdk/portal'
import type { AfterViewInit, OnDestroy, TemplateRef } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild, ViewContainerRef } from '@angular/core'
import type { IHeaderAngularComp } from 'ag-grid-angular'
import type { Column, GridApi, IHeaderParams } from 'ag-grid-community'
import { Subject } from 'rxjs'
import { takeUntil } from 'rxjs/operators'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'

@Component({
  selector: 'seed-portfolio-summary-header-menu',
  templateUrl: './portfolio-summary-header-menu.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class PortfolioSummaryHeaderMenuComponent implements IHeaderAngularComp, AfterViewInit, OnDestroy {
  @ViewChild('menu') menuTemplate!: TemplateRef<unknown>
  @ViewChild('trigger') trigger!: FlexibleConnectedPositionStrategyOrigin

  private _configService = inject(ConfigService)
  private _overlay = inject(Overlay)
  private _unsubscribeAll$ = new Subject<void>()
  private _vcr = inject(ViewContainerRef)
  column: Column<unknown>
  gridApi: GridApi
  overlayRef: OverlayRef
  params: IHeaderParams
  pinState: unknown
  scheme: 'dark' | 'light'
  sortIcon = ''

  agInit(params: IHeaderParams): void {
    this.params = params
    this.column = params.column
    this.gridApi = params.api
  }

  ngAfterViewInit(): void {
    this._configService.scheme$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((scheme) => {
      this.scheme = scheme
    })
    this._setOverlay()
    this._updateSortState()
    this.pinState = this.column.isPinned()
    this.column.addEventListener('sortChanged', () => {
      this._updateSortState()
    })
    this.gridApi.addEventListener('columnPinned', () => {
      this.pinState = this.column.isPinned()
    })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
    this.overlayRef?.dispose()
  }

  toggleMenu(): void {
    if (this.overlayRef?.hasAttached()) {
      this.overlayRef.detach()
    } else {
      const portal = new TemplatePortal(this.menuTemplate, this._vcr)
      this.overlayRef?.attach(portal)
    }
  }

  sortCol(direction: 'asc' | 'desc' | null): void {
    this.gridApi.applyColumnState({
      state: [{ colId: this.params.column.getColId(), sort: direction }],
      defaultState: { sort: null },
    })
    this._detach()
  }

  pinCol(direction: 'left' | 'right' | null): void {
    this.gridApi.setColumnsPinned([this.column], direction)
    this._detach()
  }

  hideCol(): void {
    this.gridApi.setColumnsVisible([this.column], false)
    this._detach()
  }

  refresh(): boolean {
    return true
  }

  private _updateSortState(): void {
    const state = this.gridApi.getColumnState().find((col) => col.colId === this.params.column.getColId())
    const sortDir = state?.sort ?? null
    if (sortDir === 'asc') this.sortIcon = 'fa-solid:arrow-up'
    else if (sortDir === 'desc') this.sortIcon = 'fa-solid:arrow-down'
    else this.sortIcon = ''
  }

  private _setOverlay(): void {
    const positionStrategy = this._overlay
      .position()
      .flexibleConnectedTo(this.trigger)
      .withPositions([{ originX: 'end', originY: 'bottom', overlayX: 'start', overlayY: 'top' }])

    this.overlayRef = this._overlay.create({
      positionStrategy,
      hasBackdrop: true,
      backdropClass: 'transparent-backdrop',
    })

    this.overlayRef
      .backdropClick()
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(() => {
        this.overlayRef.detach()
      })
  }

  private _detach(): void {
    this.overlayRef.detach()
  }
}
