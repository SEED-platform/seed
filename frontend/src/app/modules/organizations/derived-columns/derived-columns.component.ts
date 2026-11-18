import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { MatTableDataSource } from '@angular/material/table'
import { ActivatedRoute, Router } from '@angular/router'
import { filter, map, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { DerivedColumn } from '@seed/api'
import { DerivedColumnService, UserService } from '@seed/api'
import { DeleteModalComponent, InventoryTabComponent, PageComponent, TableContainerComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import type { InventoryDisplayType, InventoryType } from 'app/modules/inventory'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-organizations-derived-columns',
  templateUrl: './derived-columns.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [InventoryTabComponent, MaterialImports, PageComponent, SharedImports, TableContainerComponent],
})
export class DerivedColumnsComponent implements OnDestroy, OnInit {
  private _route = inject(ActivatedRoute)
  private _router = inject(Router)
  private _dialog = inject(MatDialog)
  private _userService = inject(UserService)
  private _derivedColumnService = inject(DerivedColumnService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _orgId: number
  readonly tabs: InventoryType[] = ['properties', 'taxlots']
  inventoryTypeParam = this._route.snapshot.paramMap.get('type') as InventoryType
  inventoryType: InventoryDisplayType
  derivedColumnDataSource = new MatTableDataSource<DerivedColumn>([])
  derivedColumns: DerivedColumn[]
  derivedColumnColumns = ['name', 'expression', 'actions']

  ngOnInit(): void {
    this._userService.currentOrganizationId$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((orgId) => {
          this._orgId = orgId
        }),
        switchMap(() => this._derivedColumnService.derivedColumns$),
        map((derivedColumns) => derivedColumns.sort((a, b) => naturalSort(a.name, b.name))),
        tap((derivedColumns) => {
          this.inventoryType = this.inventoryTypeParam === 'taxlots' ? 'Tax Lot' : 'Property'
          this.derivedColumns = derivedColumns.filter((dc) => dc.inventory_type === this.inventoryType)
          this.derivedColumnDataSource.data = this.derivedColumns
        }),
      )
      .subscribe()
  }

  getDerivedColumns() {
    this._derivedColumnService.get(this._orgId).subscribe()
  }

  async toggleInventoryType(type: InventoryType) {
    if (type !== this.inventoryTypeParam) {
      const newRoute = `/organizations/derived-columns/${type}`
      await this._router.navigateByUrl(newRoute, { skipLocationChange: false })
      this.inventoryTypeParam = type
      this.getDerivedColumns()
    }
  }

  createDerivedColumn = () => {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      maxHeight: '75vh',
      data: {
        derivedColumn: null,
        orgId: this._orgId,
        inventoryType: this.inventoryType,
        existingNames: this.derivedColumns.map((dc) => dc.name),
      },
    })

    dialogRef.afterClosed().subscribe(() => {
      this.getDerivedColumns()
    })
  }

  editDerivedColumn(derivedColumn: DerivedColumn) {
    const dialogRef = this._dialog.open(FormModalComponent, {
      width: '40rem',
      maxHeight: '50rem',
      data: {
        derivedColumn,
        orgId: this._orgId,
        inventoryType: this.inventoryType,
        existingNames: this.derivedColumns.map((dc) => dc.name),
      },
    })

    dialogRef.afterClosed().subscribe(() => {
      this.getDerivedColumns()
    })
  }

  deleteDerivedColumn(derivedColumn: DerivedColumn) {
    const dialogRef = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Derived Column', instance: derivedColumn.name },
    })

    dialogRef
      .afterClosed()
      .pipe(
        filter(Boolean),
        switchMap(() => this._derivedColumnService.delete({ orgId: this._orgId, id: derivedColumn.id })),
        tap(() => {
          this.getDerivedColumns()
        }),
      )
      .subscribe()
  }

  trackByFn(_index: number, { id }: DerivedColumn) {
    return id
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
