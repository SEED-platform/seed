import { CommonModule } from '@angular/common'
import { HttpClient } from '@angular/common/http'
import type { OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { forkJoin, take } from 'rxjs'
import type { Cycle, OrganizationUser, Scenario } from '@seed/api'
import { CycleService, InventoryService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import type { InventoryType } from 'app/modules/inventory/inventory.types'
import type { TimelineCycle, TimelineEvent, TimelineEventsResponse } from './timeline.types'

@Component({
  selector: 'seed-inventory-detail-timeline',
  templateUrl: './timeline.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, MaterialImports, PageComponent],
})
export class TimelineComponent implements OnInit {
  private _cycleService = inject(CycleService)
  private _httpClient = inject(HttpClient)
  private _inventoryService = inject(InventoryService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)

  cycles: Cycle[] = []
  cycleNameById: Record<number, string> = {}
  loading = true
  orgId: number
  orgUsers: OrganizationUser[] = []
  propertyId: number
  sortDesc = false
  timeline: TimelineCycle[] = []
  type: InventoryType
  viewId: number

  readonly eventLabel: Record<string, string> = {
    NoteEvent: 'Note',
    AnalysisEvent: 'Analysis',
    ATEvent: 'Audit Template Upload',
  }

  readonly eventIcon: Record<string, string> = {
    NoteEvent: 'fa-solid:note-sticky',
    AnalysisEvent: 'fa-solid:chart-line',
    ATEvent: 'fa-solid:file-import',
  }

  ngOnInit(): void {
    const params = this._route.parent?.snapshot.paramMap
    this.viewId = parseInt(params?.get('id') ?? '0')
    this.type = (params?.get('type') as InventoryType) ?? 'properties'

    this._organizationService.currentOrganization$.pipe().subscribe((org) => {
      this.orgId = org.org_id
      this.loadData()
    })
  }

  loadData(): void {
    this.loading = true
    forkJoin({
      view: this._inventoryService.getView(this.orgId, this.viewId, this.type),
      cycles: this._cycleService.cycles$.pipe(take(1)),
      users: this._organizationService.getOrganizationUsers(this.orgId),
    }).subscribe(({ view, cycles, users }) => {
      const inventoryObj = this.type === 'taxlots' ? view.taxlot : view.property
      this.propertyId = inventoryObj?.id
      this.cycles = cycles
      this.cycleNameById = cycles.reduce<Record<number, string>>((acc, c) => ({ ...acc, [c.id]: c.name }), {})
      this.orgUsers = users

      this._httpClient
        .get<TimelineEventsResponse>(`/api/v3/${this.type}/${this.propertyId}/events/`, {
          params: { organization_id: this.orgId },
        })
        .subscribe((response) => {
          this.buildTimeline(response.data ?? [])
          this.loading = false
        })
    })
  }

  buildTimeline(events: TimelineEvent[]): void {
    events.sort((a, b) =>
      this.sortDesc
        ? new Date(a.modified).getTime() - new Date(b.modified).getTime()
        : new Date(b.modified).getTime() - new Date(a.modified).getTime(),
    )

    const byCycle: Record<number, TimelineCycle> = {}
    for (const event of events) {
      if (!byCycle[event.cycle]) {
        byCycle[event.cycle] = { cycle: event.cycle, cycle_end_date: event.cycle_end_date, events: [] }
      }
      byCycle[event.cycle].events.push(event)
    }

    this.timeline = Object.values(byCycle).sort((a, b) =>
      this.sortDesc
        ? new Date(a.cycle_end_date).getTime() - new Date(b.cycle_end_date).getTime()
        : new Date(b.cycle_end_date).getTime() - new Date(a.cycle_end_date).getTime(),
    )
  }

  toggleSort(): void {
    this.sortDesc = !this.sortDesc
    this.buildTimeline(this.timeline.flatMap((c) => c.events))
  }

  userName(userId: number | null): string {
    if (!userId) return ''
    const user = this.orgUsers.find((u) => u.user_id === userId)
    if (!user) return ''
    return user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : user.email
  }

  formatDuration(start: string | null, end: string | null): string {
    if (!start || !end) return ''
    const ms = new Date(end).getTime() - new Date(start).getTime()
    const s = Math.floor(ms / 1000)
    const m = Math.floor(s / 60)
    const h = Math.floor(m / 60)
    const d = Math.floor(h / 24)
    if (d) return `${d} days`
    if (h) return `${h} hours`
    if (m) return `${m} minutes`
    return `${s} seconds`
  }

  hasMeasures(scenarios: Scenario[]): boolean {
    return scenarios?.some((s) => s.measures?.length > 0)
  }
}
