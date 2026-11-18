import { ChangeDetectionStrategy, Component, inject, type OnInit } from '@angular/core'
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { tap } from 'rxjs'
import type { GroupSystem, InventoryGroup } from '@seed/api'
import { GroupsService } from '@seed/api'
import { MaterialImports } from '@seed/materials'

export type CreateMeterDialogData = {
  orgId: number;
  groupId: number;
}

@Component({
  selector: 'seed-create-meter-dialog',
  templateUrl: './create-meter-dialog.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports, ReactiveFormsModule],
})
export class CreateMeterDialogComponent implements OnInit {
  private _dialogRef = inject(MatDialogRef<CreateMeterDialogComponent>)
  private _groupsService = inject(GroupsService)
  data = inject<CreateMeterDialogData>(MAT_DIALOG_DATA)

  systems: GroupSystem[] = []
  errorMessage: string | null = null
  submitted = false

  meterTypes = [
    'Coal (anthracite)',
    'Coal (bituminous)',
    'Coke',
    'Diesel',
    'District Chilled Water',
    'District Chilled Water - Absorption',
    'District Chilled Water - Electric',
    'District Chilled Water - Engine',
    'District Chilled Water - Other',
    'District Hot Water',
    'District Steam',
    'Electric',
    'Electric - Grid',
    'Electric - Solar',
    'Electric - Wind',
    'Fuel Oil (No. 1)',
    'Fuel Oil (No. 2)',
    'Fuel Oil (No. 4)',
    'Fuel Oil (No. 5 and No. 6)',
    'Kerosene',
    'Natural Gas',
    'Other',
    'Propane',
    'Wood',
    'Cost',
    'Electric - Unknown',
    'Custom Meter',
    'Potable Indoor',
    'Potable Outdoor',
    'Potable: Mixed Indoor/Outdoor',
  ]

  form = new FormGroup({
    system_id: new FormControl(null, Validators.required),
    type: new FormControl(null, Validators.required),
    alias: new FormControl('', Validators.required),
  })

  ngOnInit() {
    this._groupsService
      .get(this.data.orgId, this.data.groupId)
      .pipe(
        tap((group: InventoryGroup) => {
          this.systems = group.systems ?? []
        }),
      )
      .subscribe()
  }

  onSubmit() {
    if (this.form.invalid) return
    this.submitted = true
    this.errorMessage = null

    const meterData = this.form.value
    this._groupsService.createMeter(this.data.orgId, this.data.groupId, meterData).subscribe({
      next: () => {
        this._dialogRef.close(true)
      },
      error: (err: unknown) => {
        this.submitted = false
        this.errorMessage = 'Failed to create meter'
        if (err !== null && typeof err === 'object') {
          const error = err as Record<string, unknown>
          if (error.error && typeof error.error === 'object') {
            const errorDetail = error.error as Record<string, unknown>
            if (typeof errorDetail.errors === 'string') {
              this.errorMessage = errorDetail.errors
            } else if (typeof errorDetail.message === 'string') {
              this.errorMessage = errorDetail.message
            }
          }
        }
      },
    })
  }

  dismiss() {
    this._dialogRef.close()
  }
}
