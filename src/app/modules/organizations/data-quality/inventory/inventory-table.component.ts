import { CommonModule } from '@angular/common'
import type { AfterViewInit, OnChanges, OnDestroy, OnInit, SimpleChanges } from '@angular/core'
import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output, ViewChild } from '@angular/core'
import { FormsModule } from '@angular/forms'
import type { MatDialogRef } from '@angular/material/dialog'
import { MatDialog } from '@angular/material/dialog'
import { MatPaginator } from '@angular/material/paginator'
import { MatTableDataSource } from '@angular/material/table'
import { combineLatest, filter, Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { Rule } from '@seed/api'
import { ColumnService, DataQualityService, LabelService, OrganizationService } from '@seed/api'
import { DeleteModalComponent, LabelComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import type { InventoryTypeGoal } from 'app/modules/inventory/inventory.types'
import { DataQualityUtils } from '../data-quality.utils'
import { FormModalComponent } from './modal/form-modal.component'

@Component({
  selector: 'seed-data-quality-inventory-table',
  templateUrl: './inventory-table.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, FormsModule, LabelComponent, MaterialImports],
})
export class DataQualityInventoryTableComponent implements AfterViewInit, OnChanges, OnDestroy, OnInit {
  @Input() currentRules: Rule[]
  // Passed from the parent: the route component is reused across tabs, so a route snapshot here goes stale
  @Input() type: InventoryTypeGoal
  @Output() getRules = new EventEmitter<void>()
  @ViewChild(MatPaginator) paginator!: MatPaginator
  private _organizationService = inject(OrganizationService)
  private _dataQualityService = inject(DataQualityService)
  private _columnService = inject(ColumnService)
  private _labelsService = inject(LabelService)
  private _dialog = inject(MatDialog)
  readonly tabs: InventoryTypeGoal[] = ['properties', 'taxlots', 'goal']
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _orgId: number
  rulesDataSource = new MatTableDataSource<Rule>([])
  rulesColumns = ['enabled', 'field', 'severity', 'criteria', 'label', 'actions']
  propertyColumnsLookup: Record<string, string> = {}
  taxlotColumnsLookup: Record<string, string> = {}
  isOverflowing = false

  labelLookup = {}
  severityLookup = {
    0: { name: 'Error', class: 'bg-red-200 border rounded border-red-900 text-red-900' },
    1: { name: 'Warning', class: 'bg-amber-200 border rounded border-amber-900 text-amber-900' },
    2: { name: 'Valid', class: 'bg-green-200 border rounded border-green-900 text-green-900' },
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.currentRules) {
      this.rulesDataSource.data = this.currentRules
    }
  }

  ngAfterViewInit(): void {
    this.rulesDataSource.paginator = this.paginator
  }

  ngOnInit(): void {
    combineLatest([
      this._organizationService.currentOrganization$,
      this._columnService.propertyColumns$,
      this._columnService.taxLotColumns$,
      this._labelsService.labels$,
    ])
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe(([organization, propertyColumns, taxLotColumns, labels]) => {
        this._orgId = organization.id
        // The columns endpoint also returns related columns; skip them so they don't overwrite same-named fields
        for (const col of propertyColumns.filter((c) => c.table_name === 'PropertyState')) {
          this.propertyColumnsLookup[col.column_name] = col.display_name
        }
        for (const col of taxLotColumns.filter((c) => c.table_name === 'TaxLotState')) {
          this.taxlotColumnsLookup[col.column_name] = col.display_name
        }
        for (const label of labels) {
          this.labelLookup[label.id] = label
        }
      })
  }

  getFieldName(field: string): string {
    if (this.type === 'properties') {
      return this.propertyColumnsLookup[field] || field
    } else {
      return this.taxlotColumnsLookup[field] || field
    }
  }

  getCriteria(rule: Rule) {
    return DataQualityUtils.getCriteria(rule)
  }

  getRangeText(rule: Rule) {
    return DataQualityUtils.getRangeText(rule)
  }

  formatDate(dateYMD: number) {
    return DataQualityUtils.formatDate(dateYMD)
  }

  toggleEnable(index: number) {
    const rule = this.currentRules[index]
    this._dataQualityService.putRule({ rule, id: rule.id, orgId: this._orgId }).subscribe()
  }

  editRule(rule: Rule) {
    const columns$ = this.type === 'properties' ? this._columnService.propertyColumns$ : this._columnService.taxLotColumns$
    const tableName = this.type === 'properties' ? 'PropertyState' : 'TaxLotState'
    const dialogRef: MatDialogRef<FormModalComponent, boolean> = this._dialog.open(FormModalComponent, {
      width: '50rem',
      data: { rule, orgId: this._orgId, columns$, tableName, currentRules: this.currentRules },
    })
    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.getRules.emit()
        }),
      )
      .subscribe()
  }

  deleteRule(rule: Rule) {
    const displayName = `${this.getFieldName(rule.field)} ${DataQualityUtils.getCriteria(rule)}`
    const dialogRef: MatDialogRef<DeleteModalComponent, boolean> = this._dialog.open(DeleteModalComponent, {
      width: '40rem',
      data: { model: 'Rule', instance: displayName },
    })

    dialogRef
      .afterClosed()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(Boolean),
        switchMap(() => this._dataQualityService.deleteRule({ id: rule.id, orgId: this._orgId })),
        tap(() => {
          this.getRules.emit()
        }),
      )
      .subscribe()
  }

  trackByFn(index: number) {
    return index
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
