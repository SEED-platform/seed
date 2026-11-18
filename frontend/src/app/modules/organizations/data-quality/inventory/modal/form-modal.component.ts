import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { combineLatest, distinctUntilChanged, type Observable, Subject, takeUntil } from 'rxjs'
import type { Column, DataQualityFormGroup, Label, Rule } from '@seed/api'
import { DataQualityService, LabelService } from '@seed/api'
import { LabelComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { CONDITIONS, DATATYPES_BY_CONDITION, SEVERITIES, UNITS } from '../../constants'
import { DataQualityValidator } from '../../data-quality.validator'

@Component({
  selector: 'seed-organizations-members-form-modal',
  templateUrl: './form-modal.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [FormsModule, MaterialImports, LabelComponent, ReactiveFormsModule],
})
export class FormModalComponent implements OnDestroy, OnInit {
  private _dialogRef = inject(MatDialogRef<FormModalComponent>)
  private _dataQualityService = inject(DataQualityService)
  private _labelsService = inject(LabelService)
  private _dataQualityValidator = inject(DataQualityValidator)
  private readonly _unsubscribeAll$ = new Subject<void>()
  data = inject(MAT_DIALOG_DATA) as {
    rule: Rule | null;
    orgId: number;
    columns$: Observable<Column[]>;
    labels$: Observable<Label[]>;
    tableName: 'PropertyState' | 'TaxLotState' | 'Goal';
    currentRules: Rule[];
  }
  create = true
  columns: Column[]
  labels: Label[]
  labelLookup = {}

  constants = {
    conditions: CONDITIONS,
    dataTypesByCondition: DATATYPES_BY_CONDITION,
    units: UNITS,
    severities: SEVERITIES,
  }

  form: DataQualityFormGroup = new FormGroup(
    {
      condition: new FormControl<'exclude' | 'include' | 'not_null' | 'range' | 'required' | null>(null, Validators.required),
      cross_cycle: new FormControl(false), // unused
      data_type: new FormControl<number | null>(null, Validators.required),
      enabled: new FormControl(true),
      field: new FormControl<string | null>(null, Validators.required),
      for_derived_column: new FormControl(false), // hidden, set from the selected column on submit
      id: new FormControl<number | null>(null), // hidden
      max: new FormControl<number | null>(null),
      min: new FormControl<number | null>(null),
      not_null: new FormControl(false),
      required: new FormControl(false),
      rule_type: new FormControl<number | null>(null),
      severity: new FormControl<number | null>(null, Validators.required),
      status_label: new FormControl<number | null>(null),
      table_name: new FormControl<'PropertyState' | 'TaxLotState' | 'Goal' | null>(this.data.tableName), // unused
      text_match: new FormControl<string | null>(null),
      units: new FormControl(''),
    },
    {
      validators: [
        this._dataQualityValidator.hasRange(),
        this._dataQualityValidator.hasTextMatch(),
        this._dataQualityValidator.dataTypeMatch(this.data.currentRules),
        this._dataQualityValidator.hasValidLabel(),
      ],
    },
  )

  ngOnInit(): void {
    this.watchForm()

    combineLatest([this.data.columns$, this._labelsService.labels$]).subscribe(([columns, labels]) => {
      // Only offer columns that belong to this rule's table (the columns endpoint also returns related columns)
      this.columns = columns.filter((column) => column.table_name === this.data.tableName)
      this.labels = labels
      for (const label of labels) {
        this.labelLookup[label.id] = label
      }
    })

    if (this.data.rule) {
      this.create = false
      this.form.patchValue(this.data.rule)
    }
  }
  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  watchForm() {
    this.form
      .get('condition')
      ?.valueChanges.pipe(takeUntil(this._unsubscribeAll$), distinctUntilChanged())
      .subscribe((condition) => {
        this.handleConditionChange(condition)
      })
  }

  /*
   * if a condition changes check the following error scenarios
   * 1. if range and the data type is text, set the data type to null
   * 2. if exclude or include and the data type is not text, set the data type to null.
   */
  handleConditionChange(condition: string): void {
    const formDataType = this.form.get('data_type')
    // const formTextMatch = this.form.get('text_match')
    const isTextMatch = ['exclude', 'include'].includes(condition)

    const isRangeWithText = condition === 'range' && formDataType.value === 1
    const isTextMatchWithNumeric = isTextMatch && formDataType.value !== 1

    // reset data type
    if (isRangeWithText || isTextMatchWithNumeric) {
      formDataType.setValue(null)
      formDataType.markAsTouched()
    }
  }

  get dataTypes() {
    return DATATYPES_BY_CONDITION[this.form.get('condition')?.value ?? 'required']
  }

  get formErrors() {
    return this.form.errors ? (Object.values(this.form.errors) as string[]) : null
  }

  /*
   * The backend only evaluates a derived column's formula when the rule is flagged `for_derived_column`;
   * otherwise it looks the field up in extra_data, finds nothing, and the rule never fires.
   * Keep the saved flag when the field isn't in the column list (e.g. columns not loaded yet).
   */
  isDerivedField(field: string): boolean {
    const column = this.columns?.find((c) => c.column_name === field)
    if (!column) return this.form.value.for_derived_column ?? false
    return Boolean(column.derived_column)
  }

  onSubmit() {
    const rule = { ...this.form.value, for_derived_column: this.isDerivedField(this.form.value.field) } as Rule
    const fn = this.create
      ? this._dataQualityService.postRule({ rule, orgId: this.data.orgId })
      : this._dataQualityService.putRule({ rule, id: this.data.rule.id, orgId: this.data.orgId })

    fn.subscribe(() => {
      this.close()
    })
  }

  dismiss() {
    this._dialogRef.close()
  }

  close() {
    this._dialogRef.close()
  }
}
