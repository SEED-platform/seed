import { AsyncPipe } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import type { Observable } from 'rxjs'
import { Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import { InventoryService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { CrossCyclesGridComponent } from '@seed/components/cross-cycles-grid/cross-cycles-grid.component'
import type { InventoryDisplayType, InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-cross-cycles',
  templateUrl: './cross-cycles.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AsyncPipe, CrossCyclesGridComponent, PageComponent],
})
export class CrossCyclesComponent implements OnDestroy, OnInit {
  private _inventoryService = inject(InventoryService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private readonly _unsubscribeAll$ = new Subject<void>()
  displayName: InventoryDisplayType
  linkingId?: number
  type: InventoryType
  viewId: number
  viewDisplayField$: Observable<string>

  ngOnInit() {
    this.getUrlParams().subscribe()
  }

  getUrlParams() {
    return this._route.parent.paramMap.pipe(
      takeUntil(this._unsubscribeAll$),
      tap((params) => {
        this.viewId = parseInt(params.get('id'))
        this.type = params.get('type') as InventoryType
        this.displayName = this.type === 'taxlots' ? 'Tax Lot' : 'Property'
        this.linkingId = undefined
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.viewId, this.type)
      }),
      switchMap(() => this._organizationService.currentOrganization$.pipe(take(1))),
      switchMap((org) => this._inventoryService.getView(org.id, this.viewId, this.type)),
      tap((view) => {
        this.linkingId = this.type === 'taxlots' ? view.taxlot?.id : view.property?.id
      }),
    )
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
