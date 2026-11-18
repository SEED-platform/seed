import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewEncapsulation } from '@angular/core'
import { FormArray, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { finalize, Subject, takeUntil } from 'rxjs'
import type { AccessLevelsByDepth } from '@seed/api'
import { OrganizationService } from '@seed/api'
import { AlertComponent } from '@seed/components'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { arraysEqual } from '@seed/utils'
import type { EditAccessLevelsData } from '..'

@Component({
  selector: 'seed-edit-access-levels-dialog',
  templateUrl: './edit-access-levels-dialog.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AlertComponent, CommonModule, FormsModule, MaterialImports, ReactiveFormsModule, SharedImports],
})
export class EditAccessLevelsDialogComponent implements OnInit, OnDestroy {
  private _data = inject(MAT_DIALOG_DATA) as EditAccessLevelsData
  private _dialogRef = inject(MatDialogRef<EditAccessLevelsDialogComponent>)
  private _organizationService = inject(OrganizationService)

  private readonly _unsubscribeAll$ = new Subject<void>()
  originalAccessLevels = this._data.accessLevelNames
  submitted = false
  form = new FormGroup({
    levels: new FormArray(this.originalAccessLevels.map((level) => new FormControl(level, Validators.required))),
  })
  private _accessLevelInstancesByDepth: AccessLevelsByDepth

  get levels(): FormArray<FormControl<string>> {
    return this.form?.get('levels') as FormArray<FormControl<string>>
  }

  ngOnInit(): void {
    for (const control of this.levels.controls) {
      control.markAsTouched()
    }

    this.levels.valueChanges.pipe(takeUntil(this._unsubscribeAll$)).subscribe(() => {
      this._checkForDuplicates(this.levels)
    })

    this._organizationService.accessLevelInstancesByDepth$
      .pipe(takeUntil(this._unsubscribeAll$))
      .subscribe((accessLevelInstancesByDepth) => {
        this._accessLevelInstancesByDepth = accessLevelInstancesByDepth
      })
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  isLevelRemoved() {
    return this.originalAccessLevels.length > this.levels.value.length
  }

  instancesToBeRemoved() {
    const levelsRemoved = this.originalAccessLevels.length - this.levels.value.length
    return Array.from(
      { length: levelsRemoved },
      (_, i) => (this._accessLevelInstancesByDepth[this.originalAccessLevels.length - 1 - i] ?? []).length,
    ).reduce((count, length) => count + length, 0)
  }

  isValid() {
    const levels = this.levels.value.map((level) => level.trim())

    // Check for at least one level
    if (levels.length === 0) {
      return false
    }

    // Check for empty
    if (levels.some((level) => !level)) {
      return false
    }

    // Check for duplicates
    const uniqueAccessLevels = new Set(levels).size
    return levels.length === uniqueAccessLevels
  }

  addLevel(name: string) {
    const control = new FormControl(name)
    control.markAsTouched()
    this.levels.push(control)
    setTimeout(() => {
      this._checkForDuplicates(this.levels)
    })
  }

  removeLevel(index: number) {
    const levels = this.levels.value
    levels.splice(index, 1)
    this.levels.removeAt(levels.length)
    this.levels.patchValue(levels)
  }

  updateAccessLevels() {
    if (!this.submitted && this.isValid()) {
      const levels = this.levels.value.map((level) => level.trim())
      if (!arraysEqual(levels, this.originalAccessLevels)) {
        this.submitted = true
        this._organizationService
          .updateAccessLevels(this._data.organizationId, levels)
          .pipe(
            finalize(() => {
              this._dialogRef.close()
            }),
          )
          .subscribe()
      } else {
        this._dialogRef.close()
      }
    }
  }

  private _checkForDuplicates(formArray: FormArray<FormControl<string>>): void {
    // First remove any previous duplicate errors
    for (const control of formArray.controls) {
      const otherErrors: Record<string, unknown> = {}
      for (const key in control.errors) {
        if (key !== 'duplicate') {
          otherErrors[key] = control.errors[key]
        }
      }
      control.setErrors(Object.keys(otherErrors).length ? otherErrors : null)
    }

    // Check for duplicates
    for (const control of formArray.controls) {
      const { value } = control
      if (!value) continue

      // Find all controls that have the same value.
      const duplicates = formArray.controls.filter((control) => control.value === value)

      if (duplicates.length > 1) {
        control.setErrors({ ...control.errors, duplicate: true })
      }
    }
  }
}
