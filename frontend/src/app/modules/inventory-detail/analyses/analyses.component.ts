import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute } from '@angular/router'
import type { Observable } from 'rxjs'
import { filter, ReplaySubject, switchMap, takeUntil, tap } from 'rxjs'
import type { Analysis, CurrentUser, Cycle } from '@seed/api'
import { AnalysisService, CycleService, InventoryService, OrganizationService, UserService } from '@seed/api'
import { AnalysesGridComponent, NotFoundComponent, PageComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { AnalysisRunModalComponent } from 'app/modules/inventory/actions/analysis-run-modal.component'
import type { InventoryType, ViewResponse } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-analyses',
  templateUrl: './analyses.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AnalysesGridComponent, CommonModule, NotFoundComponent, PageComponent, SharedImports],
})
export class AnalysesComponent implements OnInit, OnDestroy {
  private _analysisService = inject(AnalysisService)
  private _cycleService = inject(CycleService)
  private _userService = inject(UserService)
  private _organizationService = inject(OrganizationService)
  private _inventoryService = inject(InventoryService)
  private _route = inject(ActivatedRoute)
  private _dialog = inject(MatDialog)
  private _cdr = inject(ChangeDetectorRef)
  private readonly _unsubscribeAll$ = new ReplaySubject<void>(1)
  analyses: Analysis[] = []
  cycles: Cycle[] = []
  currentUser: CurrentUser
  orgId: number
  viewDisplayField$: Observable<string>
  viewId: number
  view: ViewResponse
  type: InventoryType

  defaultColDef = {
    sortable: false,
    filter: false,
    resizable: true,
    suppressMovable: true,
  }

  ngOnInit(): void {
    this._userService.currentUser$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((user) => {
      this.currentUser = user
    })

    this.getParams()
      .pipe(
        switchMap(() => this._userService.currentOrganizationId$),
        tap((orgId) => {
          this.orgId = orgId
        }),
        switchMap(() => this._cycleService.cycles$),
        tap((cycles) => {
          this.cycles = cycles
        }),
        tap(() => {
          // Defer to avoid ExpressionChangedAfterItHasBeenCheckedError in LoadingBarComponent
          setTimeout(() => {
            this.watchAnalyses()
          })
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  getParams() {
    return this._route.parent.paramMap.pipe(
      tap((params) => {
        this.viewId = parseInt(params.get('id'))
        this.type = params.get('type') as InventoryType
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.viewId, this.type)
      }),
    )
  }

  getAnalyses() {
    return this._inventoryService.getView(this.orgId, this.viewId, this.type).pipe(
      tap((view) => {
        this.view = view
      }),
      switchMap(() => {
        const id = this.type === 'taxlots' ? this.view.taxlot.id : this.view.property.id
        return this._analysisService.getPropertyAnalyses(id)
      }),
      tap((analyses) => {
        this.analyses = analyses
        this._cdr.markForCheck()
      }),
    )
  }

  watchAnalyses() {
    this._analysisService.analyses$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(() => this.getAnalyses()),
      )
      .subscribe()
  }

  createAnalysis = () => {
    const dialogRef = this._dialog.open(AnalysisRunModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, viewIds: [this.viewId] },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this.getAnalyses()),
      )
      .subscribe()
  }

  get isViewer() {
    return this.currentUser?.org_role === 'viewer'
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
