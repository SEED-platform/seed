import type { CellValueChangedEvent, ColDef, ColGroupDef, ICellRendererParams } from 'ag-grid-community'
import { EditHeaderComponent } from '@seed/components'
import { AutocompleteCellComponent } from '@seed/components/ag-grid/autocomplete.component'
import { dataTypeOptions, unitMap } from './constants'

// Special cases
const canEdit = (to_data_type: string, field: string, isNewColumn: boolean): boolean => {
  const editMap: Record<string, boolean> = {
    to_data_type: isNewColumn,
    to_table_name: true,
    from_units: ['EUI', 'Area', 'GHG', 'GHG Intensity', 'Water use', 'WUI'].includes(to_data_type),
  }

  return editMap[field]
}

const dropdownRenderer = (params: ICellRendererParams) => {
  const value = params.value as string
  const data = params.data as { to_data_type: string; isNewColumn: boolean }
  const field = params.colDef.field

  if (!canEdit(data.to_data_type, field, data.isNewColumn)) {
    return value
  }

  return `
    <div class="flex justify-between -ml-3 w-[115%] h-full cursor-pointer">
      <span class="px-2">${value ?? ''}</span>
      <span class="material-icons text-secondary">arrow_drop_down</span>
    </div>
  `
}

const canEditClass = 'bg-primary bg-opacity-25'

const getColumnOptions = (params: ICellRendererParams, propertyColumnNames: string[], taxlotColumnNames: string[]) => {
  const data = params.data as { to_table_name: 'Property' | 'Tax Lot' }
  const to_table_name = data.to_table_name
  if (to_table_name === 'Tax Lot') {
    return taxlotColumnNames
  }
  return propertyColumnNames
}

export const buildColumnDefs = (
  propertyColumnNames: string[],
  taxlotColumnNames: string[],
  uploadedFilename: string,
  seedHeaderChange: (event: CellValueChangedEvent) => void,
  dataTypeChange: (event: CellValueChangedEvent) => void,
  validateData: (event?: CellValueChangedEvent) => void,
): (ColDef | ColGroupDef)[] => {
  const seedCols: ColDef[] = [
    { field: 'isExtraData', hide: true },
    { field: 'isNewColumn', hide: true },
    { field: 'to_field', hide: true },
    // OMIT
    {
      field: 'omit',
      headerName: 'Omit',
      cellEditor: 'agCheckboxCellEditor',
      editable: true,
      width: 70,
      onCellValueChanged: validateData,
    },
    {
      field: 'to_table_name',
      headerName: 'Inventory Type',
      headerComponent: EditHeaderComponent,
      headerComponentParams: {
        name: 'Inventory Type',
      },
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: {
        values: ['Property', 'Tax Lot'],
      },
      cellRenderer: dropdownRenderer,
      editable: true,
      cellClass: canEditClass,
    },
    // SEED HEADER
    {
      field: 'to_field_display_name',
      headerName: 'SEED Header',
      cellEditor: AutocompleteCellComponent,
      cellEditorParams: (params: ICellRendererParams) => {
        return { values: getColumnOptions(params, propertyColumnNames, taxlotColumnNames) }
      },
      headerComponent: EditHeaderComponent,
      headerComponentParams: {
        name: 'SEED Header',
      },
      onCellValueChanged: seedHeaderChange,
      editable: true,
      cellClass: canEditClass,
    },
  ]

  const fileCols: ColDef[] = [
    // DATA TYPE: Editable if isExtraData is true
    {
      field: 'to_data_type',
      headerName: 'Data Type',
      headerComponent: EditHeaderComponent,
      headerComponentParams: {
        name: 'Data Type',
      },
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: {
        values: dataTypeOptions,
      },
      cellRenderer: dropdownRenderer,
      editable: (params) => {
        const data = params?.data as { isNewColumn: boolean }
        return canEdit(null, 'to_data_type', data.isNewColumn)
      },
      onCellValueChanged: dataTypeChange,
      cellClass: (params) => {
        const data = params?.data as { isNewColumn: boolean }
        return canEdit(null, 'to_data_type', data.isNewColumn) ? canEditClass : ''
      },
    },
    /* UNITS: Only editable for Area, EUI, GHG, GHGI, Water use, WUI
     * Dropdowns are populated based on a unit type map
     */
    {
      field: 'from_units',
      headerName: 'Units',
      headerComponent: EditHeaderComponent,
      headerComponentParams: {
        name: 'Units',
      },
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: ({ data }: { data: { to_data_type: string } }) => {
        return {
          values: unitMap[data.to_data_type] ?? [],
        }
      },
      cellRenderer: dropdownRenderer,
      editable: (params) => {
        const data = params?.data as { to_data_type: string }
        return canEdit(data.to_data_type, 'from_units', null)
      },
      cellClass: (params) => {
        const data = params?.data as { to_data_type: string }
        return canEdit(data.to_data_type, 'from_units', null) ? canEditClass : ''
      },
    },
    { field: 'from_field', headerName: 'Data File Header' },
    { field: 'row1', headerName: 'Row 1' },
    { field: 'row2', headerName: 'Row 2' },
    { field: 'row3', headerName: 'Row 3' },
    { field: 'row4', headerName: 'Row 4' },
    { field: 'row5', headerName: 'Row 5' },
  ]

  const columnDefs = [
    { headerName: 'SEED', children: seedCols } as ColGroupDef,
    { headerName: uploadedFilename, children: fileCols } as ColGroupDef,
  ]

  return columnDefs
}
