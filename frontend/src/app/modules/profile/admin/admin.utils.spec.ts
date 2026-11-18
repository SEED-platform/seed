import type { AdminOrganization } from '@seed/api'
import { buildOrgTableRows, isCycleTableRow, orgNameExists, toAdminOrganizationRow } from './admin.utils'

const org = (overrides: Partial<AdminOrganization> = {}): AdminOrganization => ({
  id: 2,
  name: 'Org',
  created: '2025-01-01',
  number_of_users: 1,
  parent_id: 2,
  is_parent: true,
  user_role: 'owner',
  cycles: [],
  ...overrides,
})

describe('toAdminOrganizationRow', () => {
  it('totals counts and lists only cycles with records', () => {
    const row = toAdminOrganizationRow(
      org({
        cycles: [
          { name: '2023', cycle_id: 1, num_properties: 1200, num_taxlots: 0 },
          { name: '2024', cycle_id: 2, num_properties: 0, num_taxlots: 0 },
          { name: '2025', cycle_id: 3, num_properties: 5, num_taxlots: 7 },
        ],
      }),
    )
    expect(row.cycleCounts).toEqual([
      { cycle: '2023', properties: 1200, taxlots: 0 },
      { cycle: '2025', properties: 5, taxlots: 7 },
    ])
    expect(row.cycleTotal).toBe(3)
    expect(row.propertyTotal).toBe(1205)
    expect(row.taxlotTotal).toBe(7)
  })

  it('reports zero totals for members with no cycles and unknown totals for nonmembers', () => {
    const empty = toAdminOrganizationRow(org({ cycles: [{ name: '2024', cycle_id: 2, num_properties: 0, num_taxlots: 0 }] }))
    expect(empty.cycleCounts).toEqual([])
    expect(empty.cycleTotal).toBe(1)
    expect(empty.propertyTotal).toBe(0)

    const noCycles = toAdminOrganizationRow(org({ cycles: [] }))
    expect(noCycles.cycleCounts).toEqual([])
    expect(noCycles.cycleTotal).toBe(0)
    expect(noCycles.propertyTotal).toBe(0)
    expect(noCycles.taxlotTotal).toBe(0)

    const unknown = toAdminOrganizationRow(org({ user_role: null, cycles: undefined }))
    expect(unknown.cycleCounts).toEqual([])
    expect(unknown.cycleTotal).toBeNull()
    expect(unknown.propertyTotal).toBeNull()
    expect(unknown.taxlotTotal).toBeNull()
  })

  it('shows a parent ID only for sub-organizations', () => {
    expect(toAdminOrganizationRow(org({ id: 2, parent_id: 2 })).parentId).toBeNull()
    expect(toAdminOrganizationRow(org({ id: 2, parent_id: null })).parentId).toBeNull()
    expect(toAdminOrganizationRow(org({ id: 5, parent_id: 2, is_parent: false })).parentId).toBe(2)
  })
})

describe('orgNameExists', () => {
  it('matches existing names case-insensitively, ignoring surrounding spaces', () => {
    const orgs = [{ name: 'City of Example' }]
    expect(orgNameExists(orgs, '  city of example ')).toBeTrue()
    expect(orgNameExists(orgs, 'City of Elsewhere')).toBeFalse()
  })
})

describe('buildOrgTableRows', () => {
  it('inserts cycle rows directly after each expanded org only', () => {
    const cycles = [
      { name: '2023', cycle_id: 1, num_properties: 3, num_taxlots: 2 },
      { name: '2024', cycle_id: 2, num_properties: 5, num_taxlots: 0 },
    ]
    const a = toAdminOrganizationRow(org({ id: 1, name: 'A', cycles }))
    const b = toAdminOrganizationRow(org({ id: 2, name: 'B', cycles }))
    const rows = buildOrgTableRows([a, b], new Set([1]))
    expect(rows.map((r) => (isCycleTableRow(r) ? `${r.cycleOf.name}:${r.cycle.cycle}` : r.name))).toEqual(['A', 'A:2023', 'A:2024', 'B'])
    expect(buildOrgTableRows([a, b], new Set()).length).toBe(2)
  })
})
