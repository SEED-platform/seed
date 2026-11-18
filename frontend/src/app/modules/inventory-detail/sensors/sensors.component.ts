import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject } from '@angular/core'
import { MatDialog } from '@angular/material/dialog'
import { ActivatedRoute } from '@angular/router'
import type { Observable } from 'rxjs'
import { Subject, switchMap, takeUntil, tap } from 'rxjs'
import type { DataLogger, ReadingInterval, Sensor, SensorUsage, SensorUsageRequestConfig } from '@seed/api'
import { CycleService, DatasetService, OrganizationService, SensorService, UserService } from '@seed/api'
import { NotFoundComponent, PageComponent } from '@seed/components'
import { ConfigService } from '@seed/services'
import { DataLoggersGridComponent } from './data-loggers/data-loggers-grid.component'
import { FormModalComponent } from './data-loggers/modal/form-modal.component'
import { SensorReadingsGridComponent } from './sensor-readings/sensor-readings-grid.component'
import { SensorsGridComponent } from './sensors/sensors-grid.component'

@Component({
  selector: 'seed-inventory-detail-sensors',
  templateUrl: './sensors.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, DataLoggersGridComponent, NotFoundComponent, PageComponent, SensorsGridComponent, SensorReadingsGridComponent],
})
export class SensorsComponent implements OnDestroy, OnInit {
  private _configService = inject(ConfigService)
  private _cycleService = inject(CycleService)
  private _datasetService = inject(DatasetService)
  private _dialog = inject(MatDialog)
  private _organizationService = inject(OrganizationService)
  private _route = inject(ActivatedRoute)
  private _sensorService = inject(SensorService)
  private _userService = inject(UserService)
  private readonly _unsubscribeAll$ = new Subject<void>()

  cycleId: number
  dataLoggers: DataLogger[] = []
  datasetId: string
  excludedSensorIds: number[] = []
  excludedDataLoggerIds: number[] = []
  gridTheme$ = this._configService.gridTheme$
  interval: ReadingInterval = 'Exact'
  showOnlyOccupiedReadings = false
  orgId: number
  viewId: number
  viewDisplayField$: Observable<string>
  sensors: Sensor[]
  usage: SensorUsage

  ngOnInit() {
    this.getUrlParams()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(() => this.getOrgData()),
        tap(() => {
          this.setStreams()
        }),
      )
      .subscribe()
  }

  getUrlParams() {
    return this._route.parent.paramMap.pipe(
      tap((params) => {
        this.viewId = parseInt(params.get('id'))
        this.viewDisplayField$ = this._organizationService.getViewDisplayField(this.viewId, 'properties')
      }),
    )
  }

  getOrgData() {
    return this._userService.currentOrganizationId$.pipe(
      tap((orgId) => {
        this.orgId = orgId
      }),
      switchMap(() => this._cycleService.cycles$),
      tap((cycles) => {
        this.cycleId = cycles.length ? cycles[0].id : null
      }),
      switchMap(() => this._datasetService.datasets$),
      tap((datasets) => {
        this.datasetId = datasets.length ? datasets[0].id.toString() : null
      }),
    )
  }

  setStreams() {
    this._sensorService.listDataLoggers(this.orgId, this.viewId)
    this._sensorService.listSensors(this.orgId, this.viewId)
    this._sensorService.listSensorUsage(this.orgId, this.viewId)

    this._sensorService.dataLoggers$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((dataLoggers) => (this.dataLoggers = dataLoggers))

    this._sensorService.sensors$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((sensors) => (this.sensors = sensors))

    this._sensorService.usage$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((usage) => (this.usage = usage))
  }

  createDataLogger = () => {
    const existingDisplayNames = this.dataLoggers.map((dl) => dl.display_name)
    this._dialog.open(FormModalComponent, {
      width: '40rem',
      data: { orgId: this.orgId, viewId: this.viewId, dataLogger: null, existingDisplayNames },
    })
  }

  onDataLoggerExcludedIdsChange = (excludedIds: number[]) => {
    // unselect all sensors attached to an excluded data logger
    this.excludedDataLoggerIds = excludedIds
  }

  onSensorExcludedIdsChange = (excludedIds: number[]) => {
    this.excludedSensorIds = excludedIds
    const config = {
      excluded_sensor_ids: excludedIds,
    }
    this._sensorService.listSensorUsage(this.orgId, this.viewId, config)
  }

  onOccupiedOnlyChanged(value: boolean) {
    this.showOnlyOccupiedReadings = value
    this._sensorService.listSensorUsage(this.orgId, this.viewId, this.getConfig())
  }

  intervalChanged(interval: ReadingInterval) {
    this.interval = interval
    this._sensorService.listSensorUsage(this.orgId, this.viewId, this.getConfig())
  }

  getConfig(): SensorUsageRequestConfig {
    return {
      interval: this.interval,
      showOnlyOccupiedReadings: this.showOnlyOccupiedReadings,
      excluded_sensor_ids: this.excludedSensorIds,
    }
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
