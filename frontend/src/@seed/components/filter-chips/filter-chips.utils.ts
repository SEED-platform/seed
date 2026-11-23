import type { ColDef, GridApi } from 'ag-grid-community'
import type { Column } from '@seed/api'
import type { AgFilter, FilterSortChip, FilterType } from 'app/modules/inventory/inventory.types'

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
  inRange: ({ filter, filterTo }) => `is between ${filter} and ${filterTo}`,
}

// The lookups the legacy UI's filters use
const LEGACY_FILTER_TYPES = new Map<string, FilterType>([
  ['exact', 'equals'],
  ['icontains', 'contains'],
  ['gt', 'greaterThan'],
  ['gte', 'greaterThanOrEqual'],
  ['lt', 'lessThan'],
  ['lte', 'lessThanOrEqual'],
  ['ne', 'notEqual'],
])

/*
 * A saved filter's column and ag-grid filter model. The legacy UI's filters (e.g., in its filter groups) are strings keyed
 * by `{column}__{lookup}` (or just the column, for an exact match); those with other lookups are shown as is.
 */
const toColumnFilter = (key: string, model: unknown): [string, AgFilter] => {
  if (typeof model !== 'string') return [key, model]

  const [columnName, lookup = 'exact'] = key.split('__')
  const type = LEGACY_FILTER_TYPES.get(lookup)
  return type ? [columnName, { type, filter: model }] : [key, { type: 'equals', filter: model }]
}

/*
 * ag-grid date filters store their values in `dateFrom`/`dateTo` instead of `filter`/`filterTo`, as
 * 'YYYY-MM-DD HH:mm:ss' (or 'YYYY-MM-DDTHH:mm:ss' from the floating filter); show just the date portion.
 */
const toFilterArgs = (condition: AgFilter): FilterArgs => {
  if (condition.dateFrom === undefined && condition.dateTo === undefined) return condition
  return {
    filter: condition.dateFrom?.split(/[ T]/)[0],
    filterTo: condition.dateTo?.split(/[ T]/)[0],
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
 * Converts an ag-grid filter model (keyed by column id), which saved filters can mix with the legacy UI's, into removable
 * filter chips. `columns` is an optional fallback for the names of filtered columns that aren't in `columnDefs` (e.g., access levels).
 */
export const buildFilterChips = ({
  filterModel,
  columnDefs,
  columns = [],
}: {
  filterModel: Record<string, unknown>;
  columnDefs: ColDef[];
  columns?: Column[];
}): FilterSortChip[] => {
  return Object.entries(filterModel ?? {}).map(([key, model]) => {
    const [columnName, filter] = toColumnFilter(key, model)
    const colDef = columnDefs.find(({ colId, field }) => field === columnName || colId === columnName)
    if (colDef) {
      return {
        field: colDef.field ?? columnName,
        displayName: buildFilterDisplayName(colDef, filter),
        original: key,
      }
    }
    const column = columns.find((c) => c.name === columnName)
    return {
      field: columnName,
      displayName: buildFilterDisplayName({ headerName: column?.display_name ?? columnName }, filter),
      original: key,
    }
  })
}

/* Clears a single column's filter, leaving every other filter in place */
export const removeGridFilter = (gridApi: GridApi, columnName: string): void => {
  const currentFilters = gridApi.getFilterModel()
  Reflect.deleteProperty(currentFilters, columnName)
  gridApi.setFilterModel(currentFilters)
}
