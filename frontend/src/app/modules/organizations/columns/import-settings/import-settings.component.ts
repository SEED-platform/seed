import { ChangeDetectionStrategy, Component, inject, type OnDestroy, ViewEncapsulation } from '@angular/core'
import { FormControl, FormGroup, Validators } from '@angular/forms'
import { MatDialog } from '@angular/material/dialog'
import { Router } from '@angular/router'
import { Subject, takeUntil } from 'rxjs'
import type { Column, ProgressResponse } from '@seed/api'
import { ColumnService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { naturalSort } from '@seed/utils'
import { UpdateModalComponent } from '../modal/update-modal.component'

type ColumnChangeSet = {
  is_excluded_from_hash: boolean;
  recognize_empty: boolean;
  merge_protection?: 0 | 1;
}
@Component({
  selector: 'seed-organizations-column-import-settings',
  template: '',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports],
})
export class ImportSettingsComponent implements OnDestroy {
  protected _columnService = inject(ColumnService)
  protected readonly _unsubscribeAll$ = new Subject<void>()
  private _dialog = inject(MatDialog)
  private _router = inject(Router)
  columns: Column[]
  excludedColumns: Column[]
  emptyColumns: Column[]
  mergeProtectedColumns: Column[]
  removedExcludedColumns: Column[] = []
  removedEmptyColumns: Column[] = []
  removedMergeProtectedColumns: Column[] = []
  dirty = false
  type: string
  addEmptyForm = new FormGroup({
    column: new FormControl<number | null>(null, [Validators.required]),
  })
  addExcludeForm = new FormGroup({
    column: new FormControl<number | null>(null, [Validators.required]),
  })
  addMergeProtectedForm = new FormGroup({
    column: new FormControl<number | null>(null, [Validators.required]),
  })

  ngOnDestroy(): void {
    if (this.dirty) {
      this.save()
    }
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  async cancel() {
    this.dirty = false
    await this._router.navigate(['/organizations/columns/list'])
  }

  save(): void {
    const changes = {}
    for (const column of this.columns.filter((c) => this.columnChanged(c))) {
      changes[column.id] = this.columnChangeset(column)
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

  columnChanged(column: Column): boolean {
    if (
      this.removedEmptyColumns.includes(column)
      || this.removedExcludedColumns.includes(column)
      || this.removedMergeProtectedColumns.includes(column)
    ) {
      return true
    }
    if (this.excludedColumns.includes(column) && !column.is_excluded_from_hash) {
      return true
    }
    if (this.emptyColumns.includes(column) && !column.recognize_empty) {
      return true
    }
    if (this.mergeProtectedColumns.includes(column) && column.merge_protection === 'Favor New') {
      return true
    }
    return false
  }

  columnChangeset(column: Column): ColumnChangeSet {
    const changeset: ColumnChangeSet = {
      is_excluded_from_hash: column.is_excluded_from_hash,
      recognize_empty: column.recognize_empty,
    }
    if (this.removedEmptyColumns.includes(column)) {
      changeset.recognize_empty = false
    } else if (this.emptyColumns.includes(column)) {
      changeset.recognize_empty = true
    }
    if (this.removedExcludedColumns.includes(column)) {
      changeset.is_excluded_from_hash = false
    } else if (this.excludedColumns.includes(column)) {
      changeset.is_excluded_from_hash = true
    }
    if (this.removedMergeProtectedColumns.includes(column)) {
      changeset.merge_protection = 0 // 'Favor New'
    } else if (this.mergeProtectedColumns.includes(column)) {
      changeset.merge_protection = 1 // 'Favor Existing'
    }

    return changeset
  }

  prepareColumns(columns: Column[]) {
    this.columns = columns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.excludedColumns = columns.filter((c) => c.is_excluded_from_hash)
    this.emptyColumns = columns.filter((c) => c.recognize_empty)
    this.mergeProtectedColumns = columns.filter((c) => c.merge_protection === 'Favor Existing')
  }

  availableExcludedColumns(): Column[] {
    return this.columns.filter((c) => !c.is_excluded_from_hash)
  }

  availableEmptyColumns(): Column[] {
    return this.columns.filter((c) => !c.recognize_empty)
  }

  availableMergeProtectionColumns(): Column[] {
    return this.columns.filter((c) => c.merge_protection !== 'Favor Existing')
  }

  addExcluded() {
    this.excludedColumns.push(this.columns.find((c) => c.id === this.addExcludeForm.get('column').value))
    this.excludedColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.dirty = true
    this.addExcludeForm.reset()
  }

  addEmpty() {
    this.emptyColumns.push(this.columns.find((c) => c.id === this.addEmptyForm.get('column').value))
    this.emptyColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.dirty = true
    this.addEmptyForm.reset()
  }

  addMerge() {
    this.mergeProtectedColumns.push(this.columns.find((c) => c.id === this.addMergeProtectedForm.get('column').value))
    this.mergeProtectedColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.dirty = true
    this.addMergeProtectedForm.reset()
  }

  removeExcluded(column: Column) {
    this.excludedColumns = this.excludedColumns.filter((c) => c.id !== column.id)
    this.removedExcludedColumns.push(column)
    this.excludedColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.dirty = true
  }

  removeEmpty(column: Column) {
    this.emptyColumns = this.emptyColumns.filter((c) => c.id !== column.id)
    this.removedEmptyColumns.push(column)
    this.emptyColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.dirty = true
  }

  removeMergeProtected(column: Column) {
    this.mergeProtectedColumns = this.mergeProtectedColumns.filter((c) => c.id !== column.id)
    this.removedMergeProtectedColumns.push(column)
    this.mergeProtectedColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
    this.dirty = true
  }

  includeColumn(column: Column): boolean {
    if (column.is_excluded_from_hash) {
      return true
    } else if (column.recognize_empty) {
      return true
    } else if (column.merge_protection === 'Favor Existing') {
      return true
    }
    return false
  }
}
