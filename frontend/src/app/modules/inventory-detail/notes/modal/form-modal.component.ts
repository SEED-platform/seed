import type { OnDestroy } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Subject, takeUntil, tap } from 'rxjs'
import type { Note, NoteData } from '@seed/api'
import { NoteService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-notes-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class FormModalComponent implements OnDestroy {
  private _noteService = inject(NoteService)
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private readonly _unsubscribeAll$ = new Subject<void>()

  data = inject(MAT_DIALOG_DATA) as { orgId: number; viewId: number; type: InventoryType; note: Note }
  create = !this.data.note
  form = new FormGroup({
    text: new FormControl(this.data.note?.text ?? '', Validators.required),
  })

  onSubmit() {
    const { orgId, viewId, type, note } = this.data
    const noteData: NoteData = {
      name: 'Manually Created',
      note_type: 'Note',
      text: this.form.value.text,
    }

    const request$ = this.create
      ? this._noteService.create(orgId, viewId, noteData, type)
      : this._noteService.update(orgId, viewId, note.id, noteData, type)

    request$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.close(true)
        }),
      )
      .subscribe()
  }

  close(success = false) {
    this._dialogRef.close(success)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
