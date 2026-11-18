import { TestBed } from '@angular/core/testing'
import { MatDialog } from '@angular/material/dialog'
import { of } from 'rxjs'
import type { Column, Rule } from '@seed/api'
import { ColumnService, DataQualityService, LabelService, OrganizationService } from '@seed/api'
import { DataQualityInventoryTableComponent } from './inventory-table.component'
import { FormModalComponent } from './modal/form-modal.component'

const column = (column_name: string, display_name: string, table_name: Column['table_name']) =>
  ({ column_name, display_name, table_name, derived_column: null }) as Column

describe('DataQualityInventoryTableComponent', () => {
  const setup = async () => {
    const open = jasmine.createSpy('open').and.returnValue({ afterClosed: () => of(null) })
    const propertyColumns = [column('custom_id_1', 'Custom ID 1', 'PropertyState'), column('custom_id_1', 'Custom ID 1 (Tax Lot)', 'TaxLotState')]
    const taxLotColumns = [column('custom_id_1', 'Custom ID 1', 'TaxLotState'), column('custom_id_1', 'Custom ID 1 (Property)', 'PropertyState')]
    await TestBed.configureTestingModule({
      imports: [DataQualityInventoryTableComponent],
      providers: [
        { provide: MatDialog, useValue: { open } },
        { provide: OrganizationService, useValue: { currentOrganization$: of({ id: 1 }) } },
        { provide: ColumnService, useValue: { propertyColumns$: of(propertyColumns), taxLotColumns$: of(taxLotColumns) } },
        { provide: LabelService, useValue: { labels$: of([]) } },
        { provide: DataQualityService, useValue: {} },
      ],
    })
      .overrideComponent(DataQualityInventoryTableComponent, { set: { template: '', imports: [] } })
      .compileComponents()

    const fixture = TestBed.createComponent(DataQualityInventoryTableComponent)
    fixture.componentInstance.currentRules = []
    fixture.componentInstance.type = 'taxlots'
    fixture.detectChanges()
    return { component: fixture.componentInstance, open }
  }

  it('ignores related columns when looking up field names', async () => {
    const { component } = await setup()
    component.type = 'properties'
    expect(component.getFieldName('custom_id_1')).toBe('Custom ID 1')
    component.type = 'taxlots'
    expect(component.getFieldName('custom_id_1')).toBe('Custom ID 1')
  })

  it('edits rules for the current tab after switching tabs', async () => {
    const { component, open } = await setup()
    component.type = 'properties'
    component.editRule({ id: 1, field: 'custom_id_1' } as Rule)
    const [modal, config] = open.calls.mostRecent().args as [unknown, { data: { tableName: string } }]
    expect(modal).toBe(FormModalComponent)
    expect(config.data.tableName).toBe('PropertyState')
  })
})
