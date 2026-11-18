import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { combineLatest, Subject, take, takeUntil, tap } from 'rxjs'
import type { AccessLevelInstancesByDepth, AccessLevelsByDepth } from '@seed/api'
import { InventoryService, OrganizationService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-ali-change-modal',
  templateUrl: './ali-change-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class AliChangeModalComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<AliChangeModalComponent>)
  private _organizationService = inject(OrganizationService)
  private _inventoryService = inject(InventoryService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  accessLevelNames: AccessLevelInstancesByDepth['accessLevelNames']
  accessLevelInstancesByDepth: AccessLevelsByDepth = {}
  accessLevelInstances: AccessLevelsByDepth[keyof AccessLevelsByDepth] = []

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
  }

  form = new FormGroup({
    access_level: new FormControl<string | null>(null),
    access_level_instance: new FormControl<number | null>(null, Validators.required),
  })

  ngOnInit(): void {
    this.getTree()
    this.watchAccessLevel()
  }

  getTree() {
    combineLatest([this._organizationService.accessLevelTree$, this._organizationService.accessLevelInstancesByDepth$])
      .pipe(
        tap(([tree, accessLevelsByDepth]) => {
          this.accessLevelNames = tree.accessLevelNames
          this.accessLevelInstancesByDepth = accessLevelsByDepth
          this.getPossibleAccessLevelInstances(this.form.get('access_level')?.value)
        }),
        takeUntil(this._unsubscribeAll$),
      )
      .subscribe()
  }

  watchAccessLevel() {
    // update access level instances if the access level changes
    this.form
      .get('access_level')
      .valueChanges.pipe(
        takeUntil(this._unsubscribeAll$),
        tap((accessLevel) => {
          this.getPossibleAccessLevelInstances(accessLevel)
        }),
      )
      .subscribe()
  }

  getPossibleAccessLevelInstances(accessLevelName: string): void {
    const depth = this.accessLevelNames.findIndex((name) => name === accessLevelName)
    this.accessLevelInstances = this.accessLevelInstancesByDepth[depth]
  }

  onSubmit() {
    const { orgId, viewIds } = this.data
    const aliId = this.form.get('access_level_instance')?.value
    this._inventoryService
      .movePropertiesToAccessLevelInstance(orgId, aliId, viewIds)
      .pipe(
        take(1),
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
