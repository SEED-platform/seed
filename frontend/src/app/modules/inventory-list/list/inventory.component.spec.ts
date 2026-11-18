import type { ColDef } from 'ag-grid-community'
import type { Profile } from 'app/modules/inventory'
import { applyColumnProfile, updatePageSelection } from './inventory.component'

describe('InventoryComponent profile columns', () => {
  it('applies saved order and pins using unique API field IDs', () => {
    const profile: Profile = {
      id: 1,
      name: 'Test profile',
      inventory_type: 'Property',
      profile_location: 'List View Profile',
      columns: [
        {
          id: 11,
          column_name: 'address_line_1',
          display_name: 'Address',
          name: 'address_line_1',
          table_name: 'PropertyState',
          order: 2,
          pinned: false,
        },
        {
          id: 22,
          column_name: 'address_line_1',
          display_name: 'Address',
          name: 'address_line_1',
          table_name: 'TaxLotState',
          order: 1,
          pinned: true,
        },
      ],
    }
    const columnDefs: ColDef[] = [{ field: 'address_line_1_11' }, { field: 'address_line_1_22' }, { field: 'other' }]

    const result = applyColumnProfile(profile, columnDefs)

    expect(result.map((column) => [column.field, column.pinned])).toEqual([
      ['address_line_1_22', 'left'],
      ['address_line_1_11', null],
      ['other', undefined],
    ])
    expect(columnDefs[0].field).toBe('address_line_1_11')
  })

  it('keeps the API definitions unchanged when no profile is selected', () => {
    const columnDefs: ColDef[] = [{ field: 'address_line_1' }]
    expect(applyColumnProfile(null, columnDefs)).toBe(columnDefs)
  })
})

describe('InventoryComponent page selection', () => {
  it('preserves selected IDs from other pages while updating the current page', () => {
    expect(updatePageSelection([1, 2, 3, 4], [1, 2], [2])).toEqual([3, 4, 2])
  })

  it('removes only the current page IDs when all its rows are unchecked', () => {
    expect(updatePageSelection([1, 2, 3, 4], [1, 2], [])).toEqual([3, 4])
  })
})
