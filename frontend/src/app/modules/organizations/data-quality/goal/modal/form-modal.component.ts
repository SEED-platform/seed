import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { type Observable, Subject } from 'rxjs'
import type { Column, DataQualityFormGroup, Label, Rule } from '@seed/api'
import { DataQualityService, LabelService } from '@seed/api'
import { LabelComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { DATATYPE_LOOKUP, SEVERITIES } from '../../constants'
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
  labels: Label[]
  labelLookup = {}

  constants = {
    dataTypeLookup: DATATYPE_LOOKUP,
    severities: SEVERITIES,
  }

  form: DataQualityFormGroup = new FormGroup(
    {
      condition: new FormControl<'exclude' | 'include' | 'not_null' | 'range' | 'required' | null>(null, Validators.required),
      cross_cycle: new FormControl(false), // unused
      data_type: new FormControl<number | null>(null),
      enabled: new FormControl(true),
      field: new FormControl<string | null>(null),
      for_derived_column: new FormControl(false), // unused
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
    { validators: [this._dataQualityValidator.hasRange(), this._dataQualityValidator.hasValidLabel()] },
  )

  ngOnInit(): void {
    this._labelsService.labels$.subscribe((labels) => {
      this.labels = labels
      for (const label of labels) {
        this.labelLookup[label.id] = label
      }
    })
    this.form.patchValue(this.data.rule)
  }
  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  get formErrors() {
    return this.form.errors ? (Object.values(this.form.errors) as string[]) : null
  }

  onSubmit() {
    this._dataQualityService.putRule({ rule: this.form.value as Rule, id: this.data.rule.id, orgId: this.data.orgId }).subscribe(() => {
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
