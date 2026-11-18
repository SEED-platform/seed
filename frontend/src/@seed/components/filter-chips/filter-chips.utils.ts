import type { ColDef, GridApi } from 'ag-grid-community'
import type { Column } from '@seed/api'
import type { AgFilter, AgFilterModel, FilterSortChip, FilterType } from 'app/modules/inventory/inventory.types'

type FilterArgs = { filter?: string | number; filterTo?: string | number }

const FILTER_DESCRIPTIONS: Record<FilterType, (args: FilterArgs) => string> = {
  contains: ({ filter }) => `contains ${filter}`,
  notContains: ({ filter }) => `does not contain ${filter}`,
  equals: ({ filter }) => `= ${filter}`,
  notEqual: ({ filter }) => `!= ${filter}`,
  startsWith: ({ filter }) => `starts with ${filter}`,
  endsWith: ({ filter }) => `ends with ${filter}`,
  blank: () => 'is blank',
  notBlank: () => 'is not blank',
  greaterThan: ({ filter }) => `> ${filter}`,
  greaterThanOrEqual: ({ filter }) => `>= ${filter}`,
  lessThan: ({ filter }) => `< ${filter}`,
  lessThanOrEqual: ({ filter }) => `<= ${filter}`,
  between: ({ filter, filterTo }) => `is between ${filter} and ${filterTo}`,
}

/*
 * ag-grid date filters store their values in `dateFrom`/`dateTo` ('YYYY-MM-DD HH:mm:ss')
 * instead of `filter`/`filterTo`; show just the date portion.
 */
const toFilterArgs = (condition: AgFilter): FilterArgs => {
  if (condition.dateFrom === undefined && condition.dateTo === undefined) return condition
  return {
    filter: condition.dateFrom?.split(' ')[0],
    filterTo: condition.dateTo?.split(' ')[0],
  }
}

const describeCondition = (condition: AgFilter): string => {
  const describe = FILTER_DESCRIPTIONS[condition.type]
  return describe ? describe(toFilterArgs(condition)) : (condition.type ?? '')
}

export const buildFilterDisplayName = (colDef: ColDef, filterModel: AgFilter): string => {
  const { conditions, operator } = filterModel
  const header = colDef.headerName

  if (conditions?.length) {
    const joiner = ` ${operator?.toLowerCase() ?? 'and'} `
    return `${header} ${conditions.map(describeCondition).join(joiner)}`
  }

  return `${header} ${describeCondition(filterModel)}`
}

/*
 * Converts an ag-grid filter model (keyed by column id) into removable filter chips.
 * `columns` is an optional fallback for filters on columns that aren't in the grid.
 */
export const buildFilterChips = ({
  filterModel,
  columnDefs,
  columns = [],
}: {
  filterModel: AgFilterModel;
  columnDefs: ColDef[];
  columns?: Column[];
}): FilterSortChip[] => {
  return Object.keys(filterModel ?? {}).map((columnName) => {
    const colDef = columnDefs.find(({ colId, field }) => field === columnName || colId === columnName)
    if (colDef) {
      return {
        field: colDef.field ?? columnName,
        displayName: buildFilterDisplayName(colDef, filterModel[columnName]),
        original: columnName,
      }
    }
    const column = columns.find((c) => c.name === columnName)
    return {
      field: columnName,
      displayName: column?.display_name ?? columnName,
      original: columnName,
    }
  })
}

/* Clears a single column's filter, leaving every other filter in place */
export const removeGridFilter = (gridApi: GridApi, columnName: string): void => {
  const currentFilters = gridApi.getFilterModel()
  Reflect.deleteProperty(currentFilters, columnName)
  gridApi.setFilterModel(currentFilters)
}
