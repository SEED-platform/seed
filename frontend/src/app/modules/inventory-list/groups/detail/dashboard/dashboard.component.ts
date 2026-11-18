import { CommonModule } from '@angular/common'
import type { ElementRef, OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { ActivatedRoute } from '@angular/router'
import { Chart } from 'chart.js/auto'
import { Flow, SankeyController } from 'chartjs-chart-sankey'
import { catchError, filter, of, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { GroupDashboard, GroupSankeyEntry, OrgCycle } from '@seed/api'
import { GroupsService, MeterTypesService, OrganizationService } from '@seed/api'
import { PageComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'
import { GroupDetailLayoutComponent } from '../group-detail-layout.component'

Chart.register(SankeyController, Flow)

const SANKEY_COLORS: Record<string, string> = {
  Oil: 'black',
  'Natural Gas': 'red',
  Coal: 'gray',
  'Fossil Fuels': '#708090', // slate gray
  Electricity: 'blue',
  Energy: 'orange',
}

@Component({
  selector: 'seed-group-dashboard',
  templateUrl: './dashboard.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, MaterialImports, PageComponent],
})
export class GroupDashboardComponent implements OnDestroy, OnInit {
  @ViewChild('sankeyCanvas') sankeyCanvas: ElementRef<HTMLCanvasElement>
  private _configService = inject(ConfigService)
  private _groupsService = inject(GroupsService)
  private _meterTypesService = inject(MeterTypesService)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _chart: Chart | null = null
  private _isDark = false

  groupId = parseInt(this._route.parent.snapshot.paramMap.get('groupId'))
  layout = inject(GroupDetailLayoutComponent) // parent route component; supplies breadcrumb links
  orgId: number
  cycleId: number
  cycles: OrgCycle[] = []
  dashboard: GroupDashboard | null = null
  sankeyData: GroupSankeyEntry[] = []
  meterType = ''
  meterTypes: string[] = []
  loading = true

  ngOnInit() {
    this._configService.scheme$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap((scheme) => {
          this._isDark = scheme === 'dark'
          this._updateChart()
        }),
      )
      .subscribe()

    this._organizationService.currentOrganization$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter((org) => org?.org_id != null),
        take(1),
        tap(({ org_id }) => {
          this.orgId = org_id
        }),
        switchMap(() => this._organizationService.getById(this.orgId)),
        tap((org) => {
          this.cycles = org.cycles
          this.cycleId = org.cycles[0]?.cycle_id
        }),
        switchMap(() => this._meterTypesService.energyMeters$.pipe(take(1))),
        tap((energyMeters) => {
          this.meterTypes = energyMeters.map((m) => m.name)
          if (this.meterTypes.length) {
            this.meterType = this.meterTypes.find((t) => t === 'District Chilled Water') ?? this.meterTypes[0]
          }
        }),
        switchMap(() => this.loadDashboard()),
        switchMap(() => this.loadSankey()),
      )
      .subscribe()
  }

  loadDashboard() {
    this.loading = true
    return this._groupsService.getDashboard(this.orgId, this.groupId, this.cycleId).pipe(
      tap((data) => {
        this.dashboard = data
        this.loading = false
      }),
      catchError((err) => {
        console.error('Dashboard error:', err)
        this.dashboard = null
        this.loading = false
        return of(null)
      }),
    )
  }

  changeCycle(cycleId: number) {
    this.cycleId = cycleId
    this.loadDashboard()
      .pipe(switchMap(() => this.loadSankey()))
      .subscribe()
  }

  loadSankey() {
    if (!this.meterType) {
      this.sankeyData = []
      return of([])
    }
    return this._groupsService.getSankeyData(this.orgId, this.groupId, this.cycleId, this.meterType).pipe(
      tap((data) => {
        this.sankeyData = data
        setTimeout(() => {
          this._renderChart()
        })
      }),
    )
  }

  changeMeterType(meterType: string) {
    this.meterType = meterType
    this.loadSankey().subscribe()
  }

  ngOnDestroy() {
    this._chart?.destroy()
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  private _getColor(name: string): string {
    return SANKEY_COLORS[name] ?? 'green'
  }

  private _renderChart() {
    if (!this.sankeyCanvas?.nativeElement) return

    const chartData = this.sankeyData.filter((d) => d.flow)
    if (this._chart) {
      this._chart.destroy()
      this._chart = null
    }

    if (!chartData.length) return

    const labelColor = this._isDark ? '#e5e7eb' : '#1f2937'

    this._chart = new Chart(this.sankeyCanvas.nativeElement, {
      type: 'sankey' as unknown as 'line',
      data: {
        datasets: [
          {
            data: chartData as never,
            colorFrom: ((c: { dataset: { data: GroupSankeyEntry[] }; dataIndex: number }) =>
              this._getColor(c.dataset.data[c.dataIndex]?.from)) as never,
            colorTo: ((c: { dataset: { data: GroupSankeyEntry[] }; dataIndex: number }) =>
              this._getColor(c.dataset.data[c.dataIndex]?.to)) as never,
            borderWidth: 2,
            borderColor: 'black',
            color: labelColor,
          } as never,
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
      },
    })
  }

  private _updateChart() {
    if (!this._chart) return
    const labelColor = this._isDark ? '#e5e7eb' : '#1f2937'
    const dataset = this._chart.data.datasets[0] as unknown as Record<string, unknown>
    if (dataset) {
      dataset.color = labelColor
    }
    this._chart.update()
  }
}
