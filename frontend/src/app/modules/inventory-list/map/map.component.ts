import { NgTemplateOutlet } from '@angular/common'
import type { OnDestroy, OnInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, inject, Input } from '@angular/core'
import type { ProgressBarMode } from '@angular/material/progress-bar'
import { ActivatedRoute, Router } from '@angular/router'
import { type Feature, Overlay } from 'ol'
import { defaults as defaultControls } from 'ol/control'
import { buffer } from 'ol/extent'
import GeoJSON from 'ol/format/GeoJSON'
import WKT from 'ol/format/WKT'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import Map from 'ol/Map'
import { fromLonLat, transformExtent } from 'ol/proj'
import Cluster from 'ol/source/Cluster'
import OSM from 'ol/source/OSM'
import VectorSource from 'ol/source/Vector'
import Circle from 'ol/style/Circle'
import Fill from 'ol/style/Fill'
import Icon from 'ol/style/Icon'
import Stroke from 'ol/style/Stroke'
import Style from 'ol/style/Style'
import Text from 'ol/style/Text'
import View from 'ol/View'
import HexBin from 'ol-ext/source/HexBin'
import { filter, finalize, firstValueFrom, last, map, mergeMap, of, range, scan, Subject, switchMap, take, takeUntil, tap } from 'rxjs'
import type { CurrentUser, Label, LabelOperator, OrgCycle } from '@seed/api'
import { ColumnService, GroupsService, InventoryService, LabelService, OrganizationService, UserService } from '@seed/api'
import { NotFoundComponent, PageComponent, ProgressBarComponent } from '@seed/components'
import { MaterialImports } from '@seed/materials'
import { MapService } from '@seed/services/map'
import type { FilterResponse, InventoryType, InventoryTypeGoal, State } from 'app/modules/inventory/inventory.types'
import { LabelsComponent } from './labels.component'

type Layer = VectorLayer | TileLayer

@Component({
  selector: 'seed-inventory-list-map',
  templateUrl: './map.component.html',
  imports: [NgTemplateOutlet, LabelsComponent, MaterialImports, NotFoundComponent, PageComponent, ProgressBarComponent],
  changeDetection: ChangeDetectionStrategy.Eager,
  host: { class: 'flex flex-col flex-auto min-h-0' },
})
export class MapComponent implements OnDestroy, OnInit {
  private _columnService = inject(ColumnService)
  private _groupsService = inject(GroupsService)
  private _inventoryService = inject(InventoryService)
  private _labelService = inject(LabelService)
  private _mapService = inject(MapService)
  private _organizationService = inject(OrganizationService)
  private _router = inject(Router)
  private _userService = inject(UserService)
  private _route = inject(ActivatedRoute)
  private readonly _unsubscribeAll$ = new Subject<void>()
  private _groupPropertyIds: number[] | null = null
  private _footprintColumnName: string | null = null
  private _allColumnIds: number[] = []

  @Input() groupId?: number

  baseLayer: TileLayer
  censusTractLayer: VectorLayer
  currentUser: CurrentUser
  chunk = 250
  cycles: OrgCycle[]
  cycle: OrgCycle
  cycle$ = new Subject<void>()
  data: State[] = []
  defaultField: 'property_display_field' | 'taxlot_display_field'
  displayFieldColumnName: string
  displayFieldIsExtraData = false
  displayFieldKey: string
  filteredRecords = 0
  footprintLayer: VectorLayer
  geocodedData: State[] = []
  geocodedProperties: State[]
  geocodedTaxlots: State[]
  hexBinColor = [75, 0, 130]
  hexBinLayer: VectorLayer
  hexBinMaxOpacity = 0.8
  hexBinMinOpacity = 0.2
  hexagonSize = 750
  highlightDACs = true
  inProgress = false
  labels: Label[] = []
  layers: Record<string, { zIndex: number; visible: boolean }>
  map: Map
  orgId: number
  pointsLayer: VectorLayer
  popupInfo: { displayValue: string; viewId: number } | null = null
  popupOverlay: Overlay
  progress = { current: 0, total: 0, percent: 0, chunk: 0 }
  propertyBBLayer: VectorLayer
  propertyCentroidLayer: VectorLayer
  refreshMap$ = new Subject<void>()
  requestParams: URLSearchParams
  requestData = {}
  selectedLabels: Label[] = []
  taxlotBBLayer: VectorLayer
  taxlotCentroidLayer: VectorLayer
  type = this._route.snapshot.paramMap.get('type') as InventoryTypeGoal

  ngOnInit(): void {
    if (this.groupId) {
      this.type = 'properties'
    }
    this.defaultField = this.type === 'properties' ? 'property_display_field' : 'taxlot_display_field'
    this.getDependencies()
      .pipe(
        takeUntil(this._unsubscribeAll$),
        filter(() => !!this.cycle),
        switchMap(() => this._fetchGroupPropertyIds()),
        switchMap(() => this.initMap()),
        tap(() => {
          this.initStreams()
        }),
      )
      .subscribe()
  }

  getDependencies() {
    return this._userService.currentUser$.pipe(
      tap((currentUser) => {
        this.currentUser = currentUser
      }),
      switchMap(({ org_id }) => this._organizationService.getById(org_id)),
      tap((org) => {
        this.orgId = org.id
        this.cycles = org.cycles
        this.cycle = this.cycles.find((c) => c.cycle_id === this.currentUser.settings.cycleId) ?? this.cycles[0]
        this.displayFieldKey = this.type === 'taxlots' ? org.taxlot_display_field : org.property_display_field
      }),
      switchMap(() => (this.type === 'taxlots' ? this._columnService.taxLotColumns$ : this._columnService.propertyColumns$).pipe(take(1))),
      tap((columns) => {
        // Resolve the org display field (e.g., "Nick Name") to the column metadata
        const displayFieldCol = columns.find((c) => c.display_name === this.displayFieldKey || c.column_name === this.displayFieldKey)
        this.displayFieldKey = displayFieldCol?.name ?? this.displayFieldKey
        this.displayFieldColumnName = displayFieldCol?.column_name ?? this.displayFieldKey
        this.displayFieldIsExtraData = displayFieldCol?.is_extra_data ?? false

        // Store all column IDs so we can request extra data columns via shown_column_ids
        this._allColumnIds = columns.map((c) => c.id)

        if (this.type === 'properties') {
          const footprintCol = columns.find((c) => c.column_name === 'property_footprint')
          this._footprintColumnName = footprintCol?.name ?? null
        } else {
          this._footprintColumnName = null
        }
      }),
      switchMap(() => this.getLabels()),
    )
  }

  initStreams() {
    this.refreshMap$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        switchMap(() => this.initMap()),
      )
      .subscribe()

    this.cycle$
      .pipe(
        takeUntil(this._unsubscribeAll$),
        tap(() => {
          this.currentUser.settings.cycleId = this.cycle.cycle_id
        }),
        switchMap(() => this.updateOrgUserSettings()),
        switchMap(() => this.getLabels()),
        switchMap(() => this.initMap()),
      )
      .subscribe()
  }

  getLabels() {
    return this._labelService.getInventoryLabels(this.orgId, null, this.cycle.cycle_id, this.type as InventoryType).pipe(
      tap((labels) => {
        this.labels = labels.filter((l) => l.is_applied.length)
      }),
    )
  }

  resetMap() {
    if (this.map) {
      this.map.setTarget(null)
    }
  }

  initMap() {
    this.progress = { current: 0, total: 0, percent: 0, chunk: 0 }
    this.resetMap()

    return this.getTotalRecords().pipe(
      filter((totalPages) => {
        this.inProgress = totalPages !== 0
        if (!totalPages) this.data = []
        return this.inProgress
      }),
      switchMap((totalPages) => this.fetchRecords(totalPages)),
      map(() => {
        this.geocodeRelated()
        return
      }),
      switchMap(() => this.setLayers()),
      tap(() => {
        this.renderMap()
        this.setMapOptions()
        this.zoomCenter(this.pointsSource().getSource())
      }),
    )
  }

  getTotalRecords() {
    return this._inventoryService.getRecordCount(this.orgId, this.cycle.cycle_id, this.type).pipe(
      map((count: number) => {
        this.progress.total = count
        const totalPages = Math.ceil(count / this.chunk)
        this.progress.chunk = 100 / totalPages
        return totalPages
      }),
    )
  }

  fetchRecords(totalPages: number) {
    const inventory_type = this.type === 'properties' ? 'property' : 'taxlot'
    const include_property_ids = this._groupPropertyIds ?? []

    this.requestParams = new URLSearchParams({
      cycle: this.cycle.cycle_id.toString(),
      ids_only: 'false',
      include_related: 'true',
      page: null,
      organization_id: this.orgId.toString(),
      per_page: this.chunk.toString(),
      inventory_type,
    })

    // Only include shown_column_ids when extra data fields are needed (display field or footprints).
    // Without it, profile_id=null returns all standard fields which is sufficient for most cases.
    // When extra data IS needed, we must pass all column IDs since shown_column_ids restricts standard fields too.
    if (this.displayFieldIsExtraData && this._allColumnIds.length) {
      this.requestParams.set('shown_column_ids', this._allColumnIds.join(','))
    }

    this.requestData = {
      include_property_ids,
      filters: null,
      sorts: null,
    }

    // Fetch all records, one page at a time. mergeMap makes concurrent requests. scan accumulates results
    return range(1, totalPages).pipe(
      mergeMap((page: number) => {
        this.requestParams.set('page', page.toString())
        return this._inventoryService.getAgInventory(this.requestParams.toString(), this.requestData).pipe(
          map(({ results }: FilterResponse) => results),
          tap(() => {
            this.updateProgress()
          }),
        )
      }),
      scan((allData: State[], pageData: State[]) => [...allData, ...pageData], []), // accumulate all pages
      last(), // emit only the final result
      tap((allData: State[]) => {
        this.data = allData
        this.geocodedData = allData.filter(({ long_lat }) => long_lat)
        this.filteredRecords = this.geocodedData.length
      }),
      finalize(() => {
        // this.inProgress = false
      }),
    )
  }

  async setLayers() {
    this.layers = {
      baseLayer: { zIndex: 0, visible: true },
      censusTractLayer: { zIndex: 1, visible: true },
      hexBinLayer: { zIndex: 2, visible: this.type === 'properties' },
      propertyBBLayer: { zIndex: 3, visible: this.type === 'properties' },
      propertyCentroidLayer: { zIndex: 4, visible: this.type === 'properties' },
      taxlotBBLayer: { zIndex: 5, visible: this.type !== 'properties' },
      taxlotCentroidLayer: { zIndex: 6, visible: this.type !== 'properties' },
      pointsLayer: { zIndex: 7, visible: true },
      footprintLayer: { zIndex: 8, visible: !!this._footprintColumnName },
    }

    this.baseLayer = new TileLayer({ source: new OSM(), zIndex: this.layers.baseLayer.zIndex })

    this.pointsLayer = new VectorLayer({
      source: this.pointsSource(),
      zIndex: this.layers.pointsLayer.zIndex,
      style: (feature: Feature) => {
        const features = feature.get('features') as Feature[] | undefined
        const size: number = features ? features.length : 0
        return size > 1 ? this.clusterPointStyle(size) : this.singlePointStyle()
      },
    })

    this.propertyBBLayer = new VectorLayer({
      source: this.boundingBoxSource(this.geocodedProperties),
      zIndex: this.layers.propertyBBLayer.zIndex,
      style: this.propertyStyle(),
    })

    this.propertyCentroidLayer = new VectorLayer({
      source: this.centroidSource(this.geocodedProperties),
      zIndex: this.layers.propertyCentroidLayer.zIndex,
      style: this.propertyStyle(),
    })

    this.taxlotBBLayer = new VectorLayer({
      source: this.boundingBoxSource(this.geocodedTaxlots),
      zIndex: this.layers.taxlotBBLayer.zIndex,
      style: this.taxlotStyle(),
    })

    this.taxlotCentroidLayer = new VectorLayer({
      source: this.centroidSource(this.geocodedTaxlots),
      zIndex: this.layers.taxlotCentroidLayer.zIndex,
      style: this.taxlotStyle(),
    })

    this.footprintLayer = new VectorLayer({
      source: this.footprintSource(this.data),
      zIndex: this.layers.footprintLayer.zIndex,
      style: this.footprintStyle(),
    })

    this.censusTractLayer = new VectorLayer({
      source: await this.censusTractSource(),
      zIndex: this.layers.censusTractLayer.zIndex,
      style: (feature: Feature) => {
        const tractId = feature.get('GEOID10') as string
        const isDisadvantaged = this._mapService.isDisadvantaged(tractId)
        return new Style({
          stroke: new Stroke({ color: '#185189', width: 2 }),
          fill: isDisadvantaged && this.highlightDACs ? new Fill({ color: 'rgba(69, 130, 155, 0.4)' }) : undefined,
        })
      },
    })
    this.setHexBinLayer()
  }

  renderMap() {
    const layers = Object.entries(this.layers).reduce((acc: Layer[], [layerName, { visible }]) => {
      const layer = this[layerName] as Layer
      if (visible && layer) acc.push(layer)
      return acc
    }, [])
    this.inProgress = false

    this.map = new Map({
      target: 'map',
      layers,
      view: new View({ maxZoom: 19 }),
      controls: defaultControls({
        zoom: false,
        attribution: false,
        rotate: false,
      }),
    })
  }

  setMapOptions() {
    this.map.on('moveend', async () => {
      this.censusTractLayer.setSource(await this.censusTractSource())
    })

    const popupElement = document.getElementById('popup-element')
    if (popupElement) {
      this.popupOverlay = new Overlay({
        element: popupElement,
        positioning: 'bottom-center',
        stopEvent: true,
        autoPan: true,
        offset: [0, -10],
      })
      this.map.addOverlay(this.popupOverlay)
    }

    this.map.on('click', (event) => {
      const points: Feature[] = []

      this.map.forEachFeatureAtPixel(event.pixel, (feature, layer) => {
        // disregard hexBin/census/footprint clicks
        const ignoredZIndexes = [
          this.layers.hexBinLayer.zIndex,
          this.layers.censusTractLayer.zIndex,
          this.layers.footprintLayer.zIndex,
          undefined,
        ]
        const layerZIndex = layer?.getProperties()?.zIndex as number | undefined
        if (!ignoredZIndexes.includes(layerZIndex)) {
          points.push(...((feature.get('features') as Feature[]) ?? []))
        }
      })

      if (!points.length) {
        this.dismissPopup()
      } else if (points.length === 1) {
        this.showPointInfo(points[0])
      } else {
        this.dismissPopup()
        this.zoomOnCluster(points)
      }
    })
  }

  updateProgress() {
    this.progress.percent += this.progress.chunk
    this.progress.current = Math.min(this.progress.current + this.chunk, this.progress.total)
  }

  geocodeRelated() {
    if (this.type === 'properties') {
      this.geocodedProperties = this.data.filter(({ bounding_box }) => bounding_box)
      this.geocodedTaxlots = this.geocodedRelated()
    } else {
      this.geocodedProperties = this.geocodedRelated()
      this.geocodedTaxlots = this.data.filter(({ bounding_box }) => bounding_box)
    }
  }

  geocodedRelated() {
    // filter for only records with related
    const related: State[] = this.data.flatMap((record) => record.related?.filter((r) => r.bounding_box) || [])
    // remove duplicates based on id
    const uniqRelated: State[] = related.filter((record, idx, arr) => arr.findIndex((x) => x.id === record.id) === idx)
    return uniqRelated
  }

  // DEVELOPER NOTE: hexBin layer has serious type issues
  setHexBinLayer() {
    this.hexBinLayer = new VectorLayer({
      source: this.hexBinSource(),
      zIndex: this.layers.hexBinLayer.zIndex,
      opacity: this.hexBinMaxOpacity,
      style: (feature: Feature) => {
        const properties = feature.getProperties() as { features?: unknown[] }
        const features = properties.features || []
        const siteEUIKey = Object.keys((features[0] as { values_: Record<string, unknown> })?.values_ || {}).find((key) =>
          key.startsWith('site_eui'),
        )
        if (!siteEUIKey) {
          console.error('No site EUI key found in feature properties')
          return null
        }
        const siteEUIs = (features as { values_: Record<string, unknown> }[]).map((point) => {
          const eui = point.values_?.[siteEUIKey]
          return typeof eui === 'number' ? eui : 0
        })
        const totalEUI = siteEUIs.reduce((acc: number, eui: number) => acc + eui, 0)
        const opacity = Math.max(this.hexBinMinOpacity, totalEUI / this.hexagonSize)
        const color = [...this.hexBinColor, opacity]

        return [new Style({ fill: new Fill({ color }) })]
      },
    })
  }

  hexBinSource = (records = this.geocodedData) =>
    new HexBin({
      source: this.buildingSources(records),
      size: this.hexagonSize,
    })

  hexBinInfoBarColor() {
    const hexBinColorCode = this.hexBinColor.join(',')
    const leftColor = `rgb(${hexBinColorCode},${this.hexBinMaxOpacity * this.hexBinMinOpacity})`
    const rightColor = `rgb(${hexBinColorCode},${this.hexBinMaxOpacity})`
    return { background: `linear-gradient(to right, ${leftColor}, ${rightColor})` }
  }

  buildingSources(records: State[]) {
    const features = records.map((record) => {
      const feature = new WKT().readFeature(record.long_lat, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      })
      feature.setProperties(record)
      return feature
    })
    return new VectorSource({ features })
  }

  boundingBoxSource(records: State[]) {
    const features = records.reduce((acc: Feature[], record) => {
      if (record.bounding_box) {
        try {
          const feature = new WKT().readFeature(record.bounding_box, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857',
          })
          feature.setProperties(record)
          acc.push(feature)
        } catch (e) {
          console.error(`Failed to process bounding box for id ${record.id}:`, e)
        }
      }
      return acc
    }, [])

    return new VectorSource({ features })
  }

  centroidSource(records: State[]) {
    const features = records.reduce((acc: Feature[], record) => {
      if (record.centroid) {
        try {
          const feature = new WKT().readFeature(record.centroid, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857',
          })
          feature.setProperties(record)
          acc.push(feature)
        } catch (e) {
          console.error(`Failed to process centroid for id ${record.id}:`, e)
        }
      }
      return acc
    }, [])

    return new VectorSource({ features })
  }

  async censusTractSource() {
    let geojson = { type: 'FeatureCollection', features: [] }

    try {
      // only show census tracts at a reasonable zoom level
      if (this.map?.getView().getZoom() >= 11) {
        const extents = this.map.getView().calculateExtent(this.map.getSize())
        const [west, south, east, north] = transformExtent(extents, this.map.getView().getProjection(), 'EPSG:4326')
        const url = `https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/usa_november_2022/FeatureServer/0/query?where=1%3D1&outFields=GEOID10&geometry=${west}%2C${south}%2C${east}%2C${north}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outSR=4326&f=geojson`
        geojson = (await (await fetch(url)).json()) as { type: string; features: { properties: { GEOID10: string } }[] }
        const tractIds = geojson.features.map((feature: { properties: { GEOID10: string } }) => feature.properties.GEOID10)
        await firstValueFrom(this._mapService.checkDisadvantagedStatus(tractIds))
      }
    } catch (e) {
      console.error(e)
    }
    const features = new GeoJSON().readFeatures(geojson, {
      featureProjection: 'EPSG:3857',
    })
    return new VectorSource({ features })
  }

  clusterPointStyle(size: number) {
    const relativeRadius = 10 + Math.min(7, size / 50)
    return new Style({
      image: new Circle({
        radius: relativeRadius,
        stroke: new Stroke({ color: '#fff' }),
        fill: new Fill({ color: '#3399CC' }),
      }),
      text: new Text({
        text: size.toString(),
        fill: new Fill({ color: '#fff' }),
      }),
    })
  }

  singlePointStyle = () => new Style({ image: new Icon({ src: 'images/map_pin.webp', anchor: [0.5, 1] }) })
  pointsSource = (records = this.geocodedData) => new Cluster({ source: this.buildingSources(records), distance: 45 })
  propertyStyle = () => new Style({ stroke: new Stroke({ color: '#185189', width: 2 }) })
  taxlotStyle = () => new Style({ stroke: new Stroke({ color: '#10A0A0', width: 2 }) })
  footprintStyle = () =>
    new Style({ stroke: new Stroke({ color: '#1e3a5f', width: 2 }), fill: new Fill({ color: 'rgba(30, 58, 95, 0.2)' }) })

  footprintSource(records: State[]) {
    if (!this._footprintColumnName) return new VectorSource()
    const features = records.reduce((acc: Feature[], record) => {
      const wkt = record[this._footprintColumnName] as string | undefined
      if (wkt) {
        try {
          const feature = new WKT().readFeature(wkt, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857',
          })
          feature.setProperties(record)
          acc.push(feature)
        } catch (e) {
          console.error(`Failed to process footprint for id ${record.id}:`, e)
        }
      }
      return acc
    }, [])

    return new VectorSource({ features })
  }

  layerVisible(zIndex: number) {
    const layers = this.map.getLayers().getArray()
    return layers.some((layer) => layer.get('zIndex') === zIndex)
  }

  toggleLayer(layerName: string, visibility: boolean) {
    const layer = this.layers[layerName]
    if (layer) {
      const updatedVisibility = visibility ?? !layer.visible
      this.layers[layerName].visible = updatedVisibility
      if (updatedVisibility) {
        this.map.addLayer(this[layerName] as Layer)
      } else {
        this.map.removeLayer(this[layerName] as Layer)
      }
    }
  }

  toggleHighlightDACs() {
    this.highlightDACs = !this.highlightDACs
    this.censusTractLayer.changed()
  }

  navigateToDetail(viewId: number) {
    const typePath = this.type === 'taxlots' ? 'taxlots' : 'properties'
    void this._router.navigate(['/', typePath, viewId])
  }

  dismissPopup() {
    this.popupInfo = null
    this.popupOverlay?.setPosition(undefined)
  }

  showPointInfo(point: Feature) {
    const props = point.getProperties() as Record<string, unknown>
    const viewId = (this.type === 'taxlots' ? props.taxlot_view_id : props.property_view_id) as number
    const coordinates = (point.getGeometry() as unknown as { getCoordinates: () => number[] }).getCoordinates()

    // Resolve the display field value. The key might be exact, space-normalized, or absent (extra data fields).
    const displayValue = this._resolveDisplayValue(props)
    this.popupInfo = { displayValue: displayValue || `ID: ${viewId}`, viewId }
    this.popupOverlay?.setPosition(coordinates)
  }

  zoomOnCluster(points: Feature[]) {
    const source = new VectorSource({ features: points })
    this.zoomCenter(source, { duration: 750 })
  }

  zoomCenter(pointsSource: VectorSource, extraViewOptions = {}) {
    if (pointsSource.isEmpty()) {
      // Default view with no points is the middle of US
      const emptyView = new View({
        center: fromLonLat([-99.066067, 39.390897]),
        zoom: 4.5,
      })
      this.map.setView(emptyView)
    } else {
      const bufferedExtent = buffer(pointsSource.getExtent(), 500)
      const viewOptions = {
        size: this.map.getSize(),
        padding: [10, 10, 10, 10],
        ...extraViewOptions,
      }
      this.map.getView().fit(bufferedExtent, viewOptions)
      // this.map.getView().fit(extent, viewOptions)
    }
  }

  rerenderPoints(records: State[]) {
    this.filteredRecords = records.length
    this.pointsLayer.setSource(this.pointsSource(records))
    this.footprintLayer.setSource(this.footprintSource(records))
    if (this.type === 'properties') {
      this.hexBinLayer.setSource(this.hexBinSource(records))
      this.propertyBBLayer.setSource(this.boundingBoxSource(records))
      this.propertyCentroidLayer.setSource(this.centroidSource(records))
    } else {
      this.taxlotBBLayer.setSource(this.boundingBoxSource(records))
      this.taxlotCentroidLayer.setSource(this.centroidSource(records))
    }
  }

  updateOrgUserSettings() {
    return this._organizationService.updateOrganizationUser(this.currentUser.org_user_id, this.orgId, this.currentUser.settings)
  }

  get progressMode() {
    const mode = this.progress.current ? 'determinate' : 'indeterminate'
    return mode as ProgressBarMode
  }

  onLabelChange({ selectedLabelIds, operator }: { selectedLabelIds: number[]; operator: LabelOperator }) {
    // reset geocodedData to all data
    this.geocodedData = this.data.filter(({ long_lat }) => long_lat)

    if (!selectedLabelIds.length) {
      this.rerenderPoints(this.geocodedData)
      return
    }

    if (operator === 'and') {
      this.geocodedData = this.geocodedData.filter((record) => {
        return selectedLabelIds.every((labelId) => record.labels.includes(labelId))
      })
    } else if (operator === 'or') {
      this.geocodedData = this.geocodedData.filter((record) => {
        return selectedLabelIds.some((labelId) => record.labels.includes(labelId))
      })
    } else if (operator === 'exclude') {
      this.geocodedData = this.geocodedData.filter((record) => {
        return !selectedLabelIds.some((labelId) => record.labels.includes(labelId))
      })
    }
    this.rerenderPoints(this.geocodedData)
  }

  ngOnDestroy(): void {
    this._unsubscribeAll$.next()
    this._unsubscribeAll$.complete()
  }

  private _fetchGroupPropertyIds() {
    if (!this.groupId) {
      return of(undefined)
    }
    return this._groupsService.getProperties(this.orgId, this.groupId).pipe(
      tap((props) => {
        this._groupPropertyIds = props.map((p) => p.property_id)
      }),
    )
  }

  private _resolveDisplayValue(props: Record<string, unknown>): string {
    if (!this.displayFieldKey) return ''

    // For extra data fields, look in the nested extra_data object
    if (this.displayFieldIsExtraData) {
      const extraData = props.extra_data as Record<string, unknown> | undefined
      if (extraData) {
        // Try column_name (e.g., "Nick Name") which is how extra_data keys are stored
        const val = extraData[this.displayFieldColumnName]
        if (val !== undefined) return this._toDisplayString(val)
      }
    }

    // Try top-level exact match
    if (props[this.displayFieldKey] !== undefined) {
      return this._toDisplayString(props[this.displayFieldKey])
    }

    // Try with spaces replaced by underscores (API normalizes spaces)
    const normalized = this.displayFieldKey.replace(/ /g, '_')
    if (props[normalized] !== undefined) {
      return this._toDisplayString(props[normalized])
    }

    // Display field not found — try common fallbacks
    const fallbacks = ['property_name', 'address_line_1', 'pm_property_id', 'custom_id_1']
    for (const fallback of fallbacks) {
      const key = Object.keys(props).find((k) => k.startsWith(fallback))
      if (key) {
        const val = this._toDisplayString(props[key])
        if (val) return val
      }
    }

    return ''
  }

  private _toDisplayString(value: unknown): string {
    return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
  }
}
