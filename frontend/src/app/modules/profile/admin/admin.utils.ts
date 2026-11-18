import type { AdminOrganization } from '@seed/api'

export type CycleCount = { cycle: string; properties: number; taxlots: number }

export type AdminOrganizationRow = AdminOrganization & {
  // Sub-orgs only; a top-level org reports itself (or nothing) as its parent
  parentId: number | null;
  // Cycles with at least one property or tax lot, like the legacy admin page
  cycleCounts: CycleCount[];
  // Null when the API sent no cycle data (e.g. the requesting admin isn't a member of the org)
  cycleTotal: number | null;
  propertyTotal: number | null;
  taxlotTotal: number | null;
}

export const toAdminOrganizationRow = (org: AdminOrganization): AdminOrganizationRow => {
  const cycles = org.cycles ?? []
  const hasMembership = org.user_role !== null
  return {
    ...org,
    parentId: org.parent_id && org.parent_id !== org.id ? org.parent_id : null,
    cycleCounts: hasMembership
      ? cycles
          .filter((c) => c.num_properties || c.num_taxlots)
          .map((c) => ({ cycle: c.name, properties: c.num_properties, taxlots: c.num_taxlots }))
      : [],
    cycleTotal: hasMembership ? cycles.length : null,
    propertyTotal: hasMembership ? cycles.reduce((sum, c) => sum + c.num_properties, 0) : null,
    taxlotTotal: hasMembership ? cycles.reduce((sum, c) => sum + c.num_taxlots, 0) : null,
  }
}

export const orgNameExists = (orgs: Pick<AdminOrganization, 'name'>[], name: string): boolean => {
  const normalized = name.trim().toLowerCase()
  return orgs.some((o) => o.name.toLowerCase() === normalized)
}

// An expanded org's cycles are rendered as their own table rows, so each value sits under its column header
export type CycleTableRow = { cycleOf: AdminOrganizationRow; cycle: CycleCount }
export type OrgTableRow = AdminOrganizationRow | CycleTableRow

export const isCycleTableRow = (row: OrgTableRow): row is CycleTableRow => 'cycleOf' in row

export const buildOrgTableRows = (orgs: AdminOrganizationRow[], expandedOrgIds: ReadonlySet<number>): OrgTableRow[] =>
  orgs.flatMap((org) => [org, ...(expandedOrgIds.has(org.id) ? org.cycleCounts.map((cycle) => ({ cycleOf: org, cycle })) : [])])
