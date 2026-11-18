import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { forkJoin, Subject, switchMap, take, tap } from 'rxjs'
import { InventoryService, UbidService } from '@seed/api'
import { ModalHeaderComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from 'app/modules/inventory'

@Component({
  selector: 'seed-ubid-compare-modal',
  templateUrl: './ubid-compare.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, FormsModule, MaterialImports, ModalHeaderComponent, ReactiveFormsModule],
})
export class UbidCompareComponent implements OnInit, OnDestroy {
  private _dialogRef = inject(MatDialogRef<UbidCompareComponent>)
  private _unsubscribeAll$ = new Subject<void>()
  private _ubidService = inject(UbidService)
  private _inventoryService = inject(InventoryService)

  ubid1: string
  ubid2: string
  result: number = null

  data = inject(MAT_DIALOG_DATA) as {
    orgId: number;
    viewIds: number[];
    type: InventoryType;
  }

  form = new FormGroup({
    ubid1: new FormControl('', [Validators.required]),
    ubid2: new FormControl('', [Validators.required]),
  })

  ngOnInit(): void {
    this.getUbids()
      .pipe(
        tap(() => {
          this.patchForm()
          this.watchForm()
        }),
        take(1),
      )
      .subscribe()
  }

  getUbids() {
    const { orgId, viewIds, type } = this.data
    return forkJoin({
      view1: this._inventoryService.getView(orgId, viewIds[0], type),
      view2: this._inventoryService.getView(orgId, viewIds[1], type),
    }).pipe(
      tap(({ view1, view2 }) => {
        this.ubid1 = (view1?.state.ubid as string) || ''
        this.ubid2 = (view2?.state.ubid as string) || ''
      }),
    )
  }

  patchForm() {
    this.form.patchValue({
      ubid1: this.ubid1,
      ubid2: this.ubid2,
    })
  }

  watchForm() {
    this.watchUbid('ubid1')
    this.watchUbid('ubid2')
  }

  watchUbid(controlName: string) {
    this.form
      .get(controlName)
      ?.valueChanges.pipe(
        switchMap((value: string) => this._ubidService.validate(this.data.orgId, value)),
        tap((result) => {
          this.result = null
          this.form.get(controlName)?.setErrors(result ? null : { invalid: true })
        }),
      )
      .subscribe()
  }

  jaccardQuality(jaccard: number) {
    if (jaccard <= 0) return 'No Match'
    if (jaccard < 0.5) return 'Poor'
    return jaccard < 1 ? 'Good' : 'Perfect'
  }

  onSubmit() {
    const { ubid1, ubid2 } = this.form.value
    this._ubidService
      .compareUbids(this.data.orgId, ubid1, ubid2)
      .pipe(
        take(1),
        tap((result) => {
          this.result = result
        }),
      )
      .subscribe()
  }

  close(): void {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
