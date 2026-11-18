import { ChangeDetectionStrategy, Component, inject, type OnDestroy, ViewEncapsulation } from '@angular/core'
import { FormControl, FormGroup, Validators } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { MatTableDataSource } from '@angular/material/table'
import { Subject, takeUntil } from 'rxjs'
import type { Column, ProgressResponse } from '@seed/api'
import { ColumnService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { UpdateModalComponent } from '../modal/update-modal.component'
import { DataTypes } from './data-types.constants'

@Component({
  selector: 'seed-organizations-column-data-types-properties',
  template: '',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports],
})
export class DataTypesComponent implements OnDestroy {
  protected _columnService = inject(ColumnService)
  protected readonly _unsubscribeAll$ = new Subject<void>()
  private _dialog = inject(MatDialog)
  columns: Column[]
  columnTableDataSource = new MatTableDataSource<Column>([])
  columnTableColumns = ['display_name', 'data_type']
  type: string
  dataTypesForm = new FormGroup({})
  dataTypes = DataTypes
  isLoading = true

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  applyFilter(event: Event): void {
    const filterValue = (event.target as HTMLInputElement).value
    this.columnTableDataSource.filter = filterValue.trim().toLowerCase()
  }

  save(): void {
    const changes = {}
    for (const column of this.columns.filter((c) => c.is_extra_data)) {
      const setting = this.dataTypesForm.get(`${column.id}`).value
      if (setting !== column.data_type) {
        changes[column.id] = { data_type: setting }
      }
    }
    if (Object.keys(changes).length > 0) {
      this._columnService
        .updateMultipleColumns(this.columns[0].organization_id, this.type, changes)
        .subscribe((response: ProgressResponse) => {
          const dialogRef = this._dialog.open(UpdateModalComponent, {
            width: '40rem',
            data: { progressResponse: response },
          })
          dialogRef.afterClosed().pipe(takeUntil(this._unsubscribeAll$)).subscribe()
        })
    }
  }

  initializeFormControls() {
    for (const c of this.columns) {
      const stringId = `${c.id}`
      this.dataTypesForm.addControl(stringId, new FormControl(c.data_type, [Validators.required]))
      if (!c.is_extra_data) {
        this.dataTypesForm.get(stringId)?.disable()
      }
    }
  }
}
