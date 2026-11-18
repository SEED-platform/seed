import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormArray, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { Subject, takeUntil, tap } from 'rxjs'
import type { Column, DerivedColumn } from '@seed/api'
import { ColumnService, DerivedColumnService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { naturalSort } from '@seed/utils'
import { SEEDValidators } from '@seed/validators'
import type { InventoryDisplayType } from 'app/modules/inventory/inventory.types'
import { DerivedColumnsValidator } from '../derived-columns.validator'

@Component({
  selector: 'seed-organizations-members-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, ReactiveFormsModule],
})
export class FormModalComponent implements OnDestroy, OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _derivedColumnService = inject(DerivedColumnService)
  private _derivedColumnValidator = inject(DerivedColumnsValidator)
  private _columnService = inject(ColumnService)
  private readonly _unsubscribeAll$ = new Subject<void>()
  propertyColumns: Column[]
  taxLotColumns: Column[]

  inventoryTypes = ['Property', 'Tax Lot']
  data = inject(MAT_DIALOG_DATA) as {
    derivedColumn: DerivedColumn | null;
    orgId: number;
    inventoryType: InventoryDisplayType;
    existingNames: string[];
  }
  form = new FormGroup({
    name: new FormControl('', [
      Validators.required,
      SEEDValidators.uniqueValue(this.data.existingNames.filter((dc) => dc !== this.data.derivedColumn?.name)),
    ]),
    inventory_type: new FormControl(this.data.inventoryType, Validators.required),
    parameters: new FormArray([this.newParameter('param_a', null)]),
    expression: new FormControl('$param_a / 100', Validators.required),
  })
  update = Boolean(this.data.derivedColumn)

  get parameters(): FormArray {
    return this.form.get('parameters') as FormArray
  }

  getParameter(index: number): FormGroup {
    return this.parameters.at(index) as FormGroup
  }

  get sourceColumns(): Column[] {
    return this.form.get('inventory_type')?.value === 'Property' ? this.propertyColumns : this.taxLotColumns
  }

  ngOnInit(): void {
    this.getSourceColumns()
    this.watchExpression()
    this.watchParameters()
    this.populateForm()
  }

  addParameter(): void {
    const paramsArray = this.form.get('parameters') as FormArray
    const param_name = `param_${String.fromCharCode(96 + (paramsArray.length + 1))}`
    paramsArray.push(this.newParameter(param_name))
  }

  deleteParameter(index: number): void {
    const paramsArray = this.form.get('parameters') as FormArray
    paramsArray.removeAt(index)
  }

  /*
   * check presence of the parameter names in the expression on expression changes
   */
  watchExpression(): void {
    this.form
      .get('expression')
      ?.valueChanges.pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          const parameters = this.form.controls.parameters.controls
          for (const param of parameters) {
            param.get('parameter_name')?.markAsTouched()
            param.get('parameter_name')?.updateValueAndValidity()
          }
        }),
      )
      .subscribe()
  }

  /*
   * check for duplicate parameter names
   */
  watchParameters(): void {
    this.form
      .get('parameters')
      ?.valueChanges.pipe(
        takeUntil(this._unsubscribeAll$),
        tap((parameters) => {
          const paramNames = parameters.map((param) => param.parameter_name)
          const error = paramNames.length !== new Set(paramNames).size ? { duplicates: true } : null
          this.form.get('parameters')?.setErrors(error)
        }),
      )
      .subscribe()
  }

  /*
   * returns a new parameter form group
   */
  newParameter(name: string | null = null, sourceColumn: number | null = null) {
    const group = new FormGroup({
      parameter_name: new FormControl(name, this._derivedColumnValidator.inExpression()),
      source_column: new FormControl(sourceColumn, Validators.required),
    })
    group.get('parameter_name')?.markAsTouched()
    group.get('parameter_name')?.updateValueAndValidity()
    return group
  }

  /*
   * populate form with derived column data & disable inventory type for update
   */
  populateForm() {
    if (this.update) {
      const { name, inventory_type, expression, parameters } = this.data.derivedColumn
      this.form.patchValue({ name, inventory_type, expression })
      this.form.get('inventory_type')?.disable()
      const paramsArray = this.form.get('parameters') as FormArray
      // remove the default param_a parameter & populate with incoming parameters
      paramsArray.clear()
      for (const { parameter_name, source_column } of parameters) {
        paramsArray.push(this.newParameter(parameter_name, source_column))
      }
    }
  }

  /*
   * get property and taxlot derived columns
   */
  getSourceColumns() {
    this._columnService.propertyColumns$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((propertyColumns) => {
          this.propertyColumns = propertyColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
        }),
      )
      .subscribe()

    this._columnService.taxLotColumns$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((taxLotColumns) => {
          this.taxLotColumns = taxLotColumns.sort((a, b) => naturalSort(a.display_name, b.display_name))
        }),
      )
      .subscribe()
  }

  onSubmit(): void {
    const fn = this.update
      ? this._derivedColumnService.put({ orgId: this.data.orgId, id: this.data.derivedColumn.id, data: this.form.value as DerivedColumn })
      : this._derivedColumnService.post({ orgId: this.data.orgId, data: this.form.value as DerivedColumn })

    fn.subscribe(() => {
      this._dialogRef.close()
    })
  }

  dismiss() {
    this._dialogRef.close()
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
