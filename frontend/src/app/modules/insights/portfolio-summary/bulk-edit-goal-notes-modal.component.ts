import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Subject, takeUntil } from 'rxjs'
import { GoalService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'

const QUESTION_OPTIONS = [
  '',
  'Is this a new construction or acquisition?',
  'Do you have data to report?',
  'Is this value correct?',
  'Are these values correct?',
  'Other or multiple flags; explain in Additional Notes field',
]

@Component({
  selector: 'seed-bulk-edit-goal-notes-modal',
  templateUrl: './bulk-edit-goal-notes-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class BulkEditGoalNotesModalComponent implements OnDestroy {
  private _dialogRef = inject(MatDialogRef<BulkEditGoalNotesModalComponent>)
  private _goalService = inject(GoalService)
  private _snackBar = inject(SnackBarService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as { goalId: number; viewIds: number[] }
  questionOptions = QUESTION_OPTIONS

  form = new FormGroup({
    question_selected: new FormControl(false),
    question: new FormControl(''),
    resolution_selected: new FormControl(false),
    resolution: new FormControl(''),
    historical_note_selected: new FormControl(false),
    historical_note: new FormControl(''),
    passed_checks_selected: new FormControl(false),
    passed_checks: new FormControl(false),
    new_or_acquired_selected: new FormControl(false),
    new_or_acquired: new FormControl(false),
  })

  get isSaveDisabled(): boolean {
    const f = this.form.value
    return (
      !f.question_selected
      && !f.resolution_selected
      && !f.historical_note_selected
      && !f.passed_checks_selected
      && !f.new_or_acquired_selected
    )
  }

  onSubmit(): void {
    const f = this.form.value
    const payload: Record<string, unknown> = {}
    if (f.question_selected) payload.question = f.question || null
    if (f.resolution_selected) payload.resolution = f.resolution || null
    if (f.historical_note_selected) payload.historical_note = f.historical_note ?? ''
    if (f.passed_checks_selected) payload.passed_checks = f.passed_checks
    if (f.new_or_acquired_selected) payload.new_or_acquired = f.new_or_acquired

    this._goalService
      .bulkUpdateGoalNotes(this.data.goalId, this.data.viewIds, payload)
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((result) => {
        this._snackBar.success(result.message || 'Goal notes updated successfully.')
        this._dialogRef.close(true)
      })
  }

  close(): void {
    this._dialogRef.close(false)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
