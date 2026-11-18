import { TestBed } from '@angular/core/testing'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { of } from 'rxjs'
import type { Column, Rule } from '@seed/api'
import { DataQualityService, LabelService } from '@seed/api'
import { FormModalComponent } from './form-modal.component'

const column = (overrides: Partial<Column>): Column => ({ derived_column: null, table_name: 'PropertyState', ...overrides }) as Column

describe('FormModalComponent (data quality inventory rule)', () => {
  const setup = async (rule: Rule | null = null) => {
    const postRule = jasmine.createSpy('postRule').and.returnValue(of({}))
    const putRule = jasmine.createSpy('putRule').and.returnValue(of({}))
    const columns = [
      column({ column_name: 'site_eui', display_name: 'Site EUI' }),
      column({ column_name: 'EUI Target Dif', display_name: 'EUI Target Dif', derived_column: 7 }),
      column({ column_name: 'jurisdiction_tax_lot_id', display_name: 'Tax Lot ID', table_name: 'TaxLotState' }),
    ]
    await TestBed.configureTestingModule({
      imports: [FormModalComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: { rule, orgId: 1, columns$: of(columns), tableName: 'PropertyState', currentRules: [] },
        },
        { provide: MatDialogRef, useValue: { close: jasmine.createSpy('close') } },
        { provide: DataQualityService, useValue: { postRule, putRule } },
        { provide: LabelService, useValue: { labels$: of([]) } },
      ],
    })
      .overrideComponent(FormModalComponent, { set: { template: '', imports: [] } })
      .compileComponents()

    const fixture = TestBed.createComponent(FormModalComponent)
    fixture.detectChanges()
    return { component: fixture.componentInstance, postRule, putRule }
  }

  it('only offers columns from the rule table', async () => {
    const { component } = await setup()
    expect(component.columns.map((c) => c.column_name)).toEqual(['site_eui', 'EUI Target Dif'])
  })

  it('flags rules on derived columns so the backend evaluates the formula', async () => {
    const { component, postRule } = await setup()
    component.form.patchValue({ field: 'EUI Target Dif', condition: 'range', data_type: 0, max: 0, severity: 2, status_label: 3 })
    component.onSubmit()
    const { rule } = postRule.calls.mostRecent().args[0] as { rule: Rule }
    expect(rule.for_derived_column).toBeTrue()
  })

  it('clears the flag when an existing derived rule is moved to a regular column', async () => {
    const existing = { id: 9, field: 'EUI Target Dif', for_derived_column: true, condition: 'range', table_name: 'PropertyState' } as Rule
    const { component, putRule } = await setup(existing)
    component.form.patchValue({ field: 'site_eui' })
    component.onSubmit()
    const { rule } = putRule.calls.mostRecent().args[0] as { rule: Rule }
    expect(rule.for_derived_column).toBeFalse()
  })
})
