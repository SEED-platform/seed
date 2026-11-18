import { AsyncPipe } from '@angular/common'
import { ChangeDetectionStrategy, Component, inject, type OnInit } from '@angular/core'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'
import { AgGridAngular } from 'ag-grid-angular'
import type { ColDef } from 'ag-grid-community'
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import type { GroupMeter, MeterReadingDetail } from '@seed/api'
import { GroupsService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { ConfigService } from '@seed/services'

ModuleRegistry.registerModules([AllCommunityModule])

export type MeterReadingsDialogData = {
  orgId: number;
  meter: GroupMeter;
}

@Component({
  selector: 'seed-meter-readings-dialog',
  template: `
    <div class="ml-4 mt-4 flex gap-4" mat-dialog-title>
      <mat-icon class="text-current icon-size-5" svgIcon="fa-solid:chart-line"></mat-icon>
      <div class="text-2xl font-medium leading-6">Readings: {{ data.meter.alias }}</div>
    </div>
    <mat-divider></mat-divider>
    <mat-dialog-content class="m-4 min-h-64">
      @if (loading) {
        <p class="text-secondary">Loading readings...</p>
      } @else if (readings.length === 0) {
        <p class="text-secondary">No readings found for this meter.</p>
      } @else {
        <p class="text-hint mb-2 text-xs">{{ readings.length }} readings</p>
        <div class="h-80">
          <ag-grid-angular
            class="h-full w-full"
            [theme]="gridTheme$ | async"
            [rowData]="readings"
            [columnDefs]="columnDefs"
            [defaultColDef]="defaultColDef"
          />
        </div>
      }
    </mat-dialog-content>
    <div class="flex items-center justify-end gap-2 bg-gray-50 px-6 py-4 dark:bg-black dark:bg-opacity-10">
      <button mat-stroked-button mat-dialog-close>Close</button>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [AgGridAngular, AsyncPipe, MaterialImports],
})
export class MeterReadingsDialogComponent implements OnInit {
  private _configService = inject(ConfigService)
  private _groupsService = inject(GroupsService)
  dialogRef = inject(MatDialogRef<MeterReadingsDialogComponent>)
  data = inject<MeterReadingsDialogData>(MAT_DIALOG_DATA)
  gridTheme$ = this._configService.gridTheme$

  loading = true
  readings: MeterReadingDetail[] = []
  columnDefs: ColDef[] = [
    { headerName: 'Start Time', field: 'start_time', flex: 1 },
    { headerName: 'End Time', field: 'end_time', flex: 1 },
    { headerName: 'Reading', field: 'reading', flex: 1 },
    { headerName: 'Unit', field: 'source_unit', width: 100 },
  ]

  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true,
  }

  ngOnInit() {
    this._groupsService.getMeterReadings(this.data.orgId, this.data.meter.id).subscribe({
      next: (readings) => {
        this.readings = readings
        this.loading = false
      },
      error: () => {
        this.readings = []
        this.loading = false
      },
    })
  }
}
