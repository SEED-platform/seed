import { CdkDrag, type CdkDragDrop, CdkDropList, moveItemInArray } from '@angular/cdk/drag-drop'
import { NgTemplateOutlet } from '@angular/common'
import { ChangeDetectionStrategy, Component, HostListener, inject, type OnDestroy, ViewEncapsulation } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { TranslocoService } from '@jsverse/transloco'
import type { Observable } from 'rxjs'
import { finalize, last, Subject, switchMap, takeUntil } from 'rxjs'
import type { Column, ProgressResponse } from '@seed/api'
import { ColumnService } from '@seed/api'
import { SharedImports } from '@seed/directives'
import type { ComponentCanDeactivate } from '@seed/guards/pending-changes.guard'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services/uploader/uploader.service'
import type { ProgressBarObj } from '@seed/services/uploader/uploader.types'
import { naturalSort } from '@seed/utils'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

@Component({
  selector: 'seed-organizations-column-geocoding-properties',
  templateUrl: './geocoding.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports, CdkDropList, CdkDrag, MaterialImports, NgTemplateOutlet, ReactiveFormsModule],
})
export class GeocodingComponent implements ComponentCanDeactivate, OnDestroy {
  protected _columnService = inject(ColumnService)
  protected readonly _unsubscribeAll$ = new Subject<void>()
  private _uploaderService = inject(UploaderService)
  private _snackBar = inject(SnackBarService)
  private _transloco = inject(TranslocoService)
  // required by the progress poller; this page shows a "Saving…" state rather than a progress bar
  private _progressBarObj: ProgressBarObj = {
    message: '',
    progress: 0,
    complete: false,
    statusMessage: '',
    progressLastUpdated: null,
    progressLastChecked: null,
  }
  columns: Column[] = []
  availableColumns: Column[] = []
  type: string
  saving = false
  // Column ids, in order, as last loaded from / saved to the server
  private _savedColumnIds: number[] = []
  private _allColumns: Column[] = []
  addForm = new FormGroup({
    addGeocoder: new FormControl<number>(null, [Validators.required]),
  })

  get hasUnsavedChanges(): boolean {
    const currentIds = this.columns.map((c) => c.id)
    if (currentIds.length !== this._savedColumnIds.length) {
      return true
    }
    return currentIds.some((id, i) => id !== this._savedColumnIds[i])
  }

  /** Used by PendingChangesGuard for in-app navigation, and by the browser on reload/close */
  @HostListener('window:beforeunload')
  canDeactivate(): boolean {
    // returning false prompts the user before leaving
    return !this.hasUnsavedChanges
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  drop(event: CdkDragDrop<string[]>) {
    moveItemInArray(this.columns, event.previousIndex, event.currentIndex)
  }

  remove(column: Column) {
    this.columns = this.columns.filter((c) => c.id !== column.id)
    this.availableColumns = [...this.availableColumns, column].sort((a, b) => naturalSort(a.display_name, b.display_name))
  }

  add() {
    const columnToAdd = this.availableColumns.find((c) => c.id === this.addForm.value.addGeocoder)
    if (!columnToAdd || this.saving) {
      return
    }
    this.availableColumns = this.availableColumns.filter((c) => c.id !== columnToAdd.id)
    this.columns = [...this.columns, columnToAdd]
    this.addForm.reset()
  }

  save() {
    const organizationId = this._allColumns[0]?.organization_id
    if (!organizationId) {
      return
    }
    const changes: Record<number, { geocoding_order: number }> = {}
    for (const [i, column] of this.columns.entries()) {
      changes[column.id] = { geocoding_order: i + 1 }
    }
    // anything that was saved previously but is no longer in the list gets removed from geocoding
    const currentIds = new Set(this.columns.map((c) => c.id))
    for (const id of this._savedColumnIds.filter((savedId) => !currentIds.has(savedId))) {
      changes[id] = { geocoding_order: 0 }
    }
    this.saving = true
    this._columnService
      .updateMultipleColumns(organizationId, this.type, changes)
      .pipe(
        // the update runs as a background task; poll it until it finishes and keep only the final status
        switchMap((response: ProgressResponse) =>
          this._uploaderService.checkProgressLoop({
            progressKey: response.progress_key,
            progressBarObj: this._progressBarObj,
            failureFn: () => {
              this._showSaveFailed()
            },
          }),
        ),
        last(),
        finalize(() => {
          this.saving = false
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe({
        next: (response: ProgressResponse) => {
          if (response?.status === 'success') {
            this._onSaveSuccess(organizationId)
          } else {
            this._showSaveFailed()
          }
        },
        // request errors are already reported by ErrorService, and progress errors by failureFn above
        error: () => undefined,
      })
  }

  private _onSaveSuccess(organizationId: number) {
    this._savedColumnIds = this.columns.map((c) => c.id)
    this._snackBar.success(this._transloco.translate('Columns Updated'))
    // reload so the cached columns (shared with other pages) reflect the saved order
    this.refreshColumns(organizationId).subscribe()
  }

  private _showSaveFailed() {
    this._snackBar.alert(this._transloco.translate('Failed to update columns'))
  }

  /** Subclasses return the column stream for their inventory type */
  protected refreshColumns(_organizationId: number): Observable<Column[]> {
    throw new Error('refreshColumns must be implemented by a subclass')
  }

  /** Resets the page to the given server state (copies the array so the cached columns aren't mutated) */
  protected setColumns(columns: Column[]) {
    this._allColumns = [...columns]
    this.columns = this._allColumns.filter((c) => c.geocoding_order !== 0).sort((a, b) => a.geocoding_order - b.geocoding_order)
    this.availableColumns = this._allColumns
      .filter((c) => c.geocoding_order === 0)
      .sort((a, b) => naturalSort(a.display_name, b.display_name))
    this._savedColumnIds = this.columns.map((c) => c.id)
  }
}
