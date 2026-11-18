import { CommonModule } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import type { MatStepper } from '@angular/material/stepper'
import { ActivatedRoute } from '@angular/router'
import { catchError, filter, forkJoin, of, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type {
  Column,
  ColumnMappingProfile,
  ColumnMappingProfileType,
  Cycle,
  ImportFile,
  MappingResultsResponse,
  MappingSuggestionsResponse,
  Organization,
  ProgressResponse,
} from '@seed/api'
import {
  CacheService,
  ColumnMappingProfileService,
  ColumnService,
  CycleService,
  DatasetService,
  MappingService,
  OrganizationService,
  UserService,
} from '@seed/api'
import { PageComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { UploaderService } from '@seed/services/uploader'
import { SnackBarService } from 'app/core/snack-bar/snack-bar.service'
import type { InventoryDisplayType, InventoryType, Profile } from 'app/modules/inventory'
import { HelpComponent } from './help.component'
import { MapDataComponent } from './step1/map-data.component'
import { SaveMappingsComponent } from './step3/save-mappings.component'
import { MatchMergeComponent } from './step4/match-merge.component'

@Component({
  selector: 'seed-data-mapping-stepper',
  templateUrl: './data-mapping.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [
    CommonModule,
    FormsModule,
    HelpComponent,
    MapDataComponent,
    MatchMergeComponent,
    MaterialImports,
    PageComponent,
    ProgressBarComponent,
    ReactiveFormsModule,
    SaveMappingsComponent,
  ],
})
export class DataMappingComponent implements OnDestroy, OnInit {
  @ViewChild('stepper') stepper!: MatStepper
  @ViewChild(MapDataComponent) mapDataComponent!: MapDataComponent
  @ViewChild(MatchMergeComponent) matchMergeComponent!: MatchMergeComponent
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _cacheService = inject(CacheService)
  private _columnMappingProfileService = inject(ColumnMappingProfileService)
  private _columnService = inject(ColumnService)
  private _cycleService = inject(CycleService)
  private _datasetService = inject(DatasetService)
  private _mappingService = inject(MappingService)
  private _organizationService = inject(OrganizationService)
  private _snackBar = inject(SnackBarService)
  private _router = inject(ActivatedRoute)
  private _uploaderService = inject(UploaderService)
  private _userService = inject(UserService)
  columns: Column[]
  columnMappingProfiles: ColumnMappingProfile[] = []
  columnMappingProfileTypes: ColumnMappingProfileType[]
  columnNames: string[]
  completed = { 1: false, 2: false, 3: false, 4: false }
  currentProfile: Profile
  cycle: Cycle
  datasetId: number
  fileId = this._router.snapshot.params.id as number
  firstFiveRows: Record<string, unknown>[]
  helpOpened = false
  importFile: ImportFile
  inventoryType: InventoryType = 'properties'
  mappingResultsResponse: MappingResultsResponse
  mappingSuggestions: MappingSuggestionsResponse
  matchingPropertyColumnDisplayNames = ''
  matchingPropertyColumns: string[] = []
  matchingTaxLotColumnDisplayNames = ''
  matchingTaxLotColumns: string[] = []
  org: Organization
  orgId: number
  progressBarObj = this._uploaderService.defaultProgressBarObj
  progressTitle = 'Mapping Data...'
  propertyColumns: Column[]
  rawColumnNames: string[] = []
  taxlotColumns: Column[]

  ngOnInit(): void {
    // this._userService.currentOrganizationId$
    this._organizationService.currentOrganization$
      .pipe(
        take(1),
        tap((org) => {
          this.orgId = org.id
          this.org = org
        }),
        switchMap(() => this.getImportFile()),
        filter(Boolean),
        tap(() => {
          this.getProfiles()
        }),
        switchMap(() => this.getMappingData()),
        switchMap(() => this.getColumns()),
      )
      .subscribe()
  }

  getImportFile() {
    return this._datasetService.getImportFile(this.orgId, this.fileId).pipe(
      take(1),
      tap((importFile) => {
        this.importFile = importFile
        this.datasetId = importFile.dataset?.id
        this.columnMappingProfileTypes
          = importFile.source_type === 'BuildingSync Raw' ? ['BuildingSync Default', 'BuildingSync Custom'] : ['Normal']
      }),
      catchError(() => {
        return of(null)
      }),
    )
  }

  getMappingData() {
    return forkJoin([
      this._cycleService.getCycle(this.orgId, this.importFile.cycle),
      this._mappingService.firstFiveRows(this.orgId, this.fileId),
      this._mappingService.mappingSuggestions(this.orgId, this.fileId),
      this._mappingService.rawColumnNames(this.orgId, this.fileId),
    ]).pipe(
      take(1),
      tap(([cycle, firstFiveRows, mappingSuggestions, rawColumnNames]) => {
        this.cycle = cycle
        this.firstFiveRows = firstFiveRows
        this.mappingSuggestions = mappingSuggestions
        this.rawColumnNames = rawColumnNames
      }),
    )
  }

  getColumns() {
    return forkJoin([
      this._organizationService.getMatchingCriteriaColumns(this.orgId, 'properties'),
      this._organizationService.getMatchingCriteriaColumns(this.orgId, 'taxlots'),
      this._columnService.propertyColumns$.pipe(take(1)),
      this._columnService.taxLotColumns$.pipe(take(1)),
    ]).pipe(
      take(1),
      tap(([matchingPropertyColumns, matchingTaxLotColumns, propertyColumns, taxlotColumns]) => {
        this.matchingPropertyColumns = matchingPropertyColumns as string[]
        this.matchingTaxLotColumns = matchingTaxLotColumns as string[]
        this.propertyColumns = propertyColumns
        this.taxlotColumns = taxlotColumns

        const propertyMap = new Map(
          propertyColumns.filter((c) => c.table_name === 'PropertyState').map((c) => [c.column_name, c.display_name]),
        )
        const taxlotMap = new Map(taxlotColumns.filter((c) => c.table_name === 'TaxLotState').map((c) => [c.column_name, c.display_name]))

        this.matchingPropertyColumnDisplayNames = this.matchingPropertyColumns.map((name) => propertyMap.get(name) || name).join(', ')
        this.matchingTaxLotColumnDisplayNames = this.matchingTaxLotColumns.map((name) => taxlotMap.get(name) || name).join(', ')
      }),
    )
  }

  getProfiles() {
    this._columnMappingProfileService
      .getProfiles(this.orgId, this.columnMappingProfileTypes)
      .pipe(
        switchMap(() => this._columnMappingProfileService.profiles$),
        takeUntil(this._unsubscribeAll$),
        tap((profiles) => {
          this.columnMappingProfiles = profiles
        }),
      )
      .subscribe()
  }

  onCompleted(step: number) {
    this.completed[step] = true
    this.stepper.next()
  }

  startMapping() {
    const mappedData = this.mapDataComponent.mappedData
    this.columns = this.mapDataComponent.defaultInventoryType === 'Tax Lot' ? this.taxlotColumns : this.propertyColumns
    this.nextStep(1)

    const failureFn = () => {
      this._snackBar.alert('Error starting mapping')
    }
    const successFn = () => {
      this.getMappingResults()
    }

    this._mappingService
      .startMapping(this.orgId, this.fileId, mappedData)
      .pipe(
        switchMap(() => this._mappingService.remapBuildings(this.orgId, this.fileId)),
        tap((response: ProgressResponse) => {
          this.progressBarObj.progress = response.progress
        }),
        switchMap((data) => {
          if (data.progress === 100) {
            successFn()
            return of(null)
          }

          return this._uploaderService.checkProgressLoop({
            progressKey: data.progress_key,
            successFn,
            failureFn,
            progressBarObj: this.progressBarObj,
          })
        }),
        takeUntil(this._unsubscribeAll$),
        catchError((error) => {
          console.log('Error starting mapping:', error)
          return of(null)
        }),
      )
      .subscribe()
  }

  getMappingResults(): void {
    this.progressTitle = 'Fetching Mapping Results...'
    const successFn = ({ unique_id }: ProgressResponse) => {
      this._cacheService
        .getCacheEntry(this.orgId, unique_id)
        .pipe(
          tap((response) => {
            this.mappingResultsResponse = response as MappingResultsResponse
            this.nextStep(2)
          }),
          take(1),
        )
        .subscribe()
    }

    this._mappingService
      .mappingResults(this.orgId, this.fileId)
      .pipe(
        switchMap(({ progress_key }) =>
          this._uploaderService.checkProgressLoop({
            progressKey: progress_key,
            successFn,
            progressBarObj: this.progressBarObj,
          }),
        ),
      )
      .subscribe()
  }

  startMatchMerge() {
    this.nextStep(3)
    this.matchMergeComponent.startMatchMerge()
  }

  onMatchComplete() {
    this.completed[4] = true
  }

  nextStep(currentStep: number) {
    this.completed[currentStep] = true
    setTimeout(() => {
      this.stepper.next()
    })
  }

  backToMapping() {
    this.stepper.selectedIndex = 0
    this.completed = { 1: false, 2: false, 3: false, 4: false }
  }

  toggleHelp = () => {
    this.helpOpened = !this.helpOpened
  }

  onDefaultInventoryTypeChange(value: InventoryDisplayType) {
    this.inventoryType = value === 'Tax Lot' ? 'taxlots' : 'properties'
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }
}
