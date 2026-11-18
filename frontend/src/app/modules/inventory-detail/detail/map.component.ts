import type { AfterViewInit } from '@angular/core'
import { ChangeDetectionStrategy, Component, Input } from '@angular/core'
import { defaults as defaultControls } from 'ol/control'
import WKT from 'ol/format/WKT'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import Map from 'ol/Map'
import { fromLonLat } from 'ol/proj'
import Cluster from 'ol/source/Cluster'
import OSM from 'ol/source/OSM'
import VectorSource from 'ol/source/Vector'
import Stroke from 'ol/style/Stroke'
import Style from 'ol/style/Style'
import View from 'ol/View'
import { MaterialImports } from '@seed/materials'
import type { InventoryType, State } from 'app/modules/inventory/inventory.types'

@Component({
  selector: 'seed-inventory-detail-map',
  templateUrl: './map.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [MaterialImports],
})
export class MapComponent implements AfterViewInit {
  @Input() state: State
  @Input() type: InventoryType

  baseLayer: TileLayer
  boundingBox: unknown
  buildingBBLayer: VectorLayer
  buildingCentroidLayer: VectorLayer
  buildingStyle: Style
  centroid: unknown
  clusterSource: Cluster
  geocodedData: State[]
  geocodedProperties: State[]
  geocodedTaxLots: State[]
  layers: Record<string, { zIndex: number; visible: number }>
  map: Map
  taxlotBBLayer: VectorLayer
  taxlotCentroidLayer: VectorLayer
  taxlotStyle: Style
  unGeocodedData: State[]

  ngAfterViewInit() {
    this.initMap()
  }

  initMap() {
    this.resetMap()
    this.buildGeocodedInventory()
    this.setGeocodedData()
    this.buildLayers()
    this.setBaseLayer()
    this.setCluster()
    this.setStyles()
    this.setLayers()
    this.renderMap()
    this.zoomCenter(this.clusterSource.getSource())
    this.styleMap()
  }

  resetMap() {
    if (this.map) {
      this.map.setTarget(null)
    }
  }

  buildGeocodedInventory() {
    if (this.type === 'properties') {
      this.geocodedProperties = this.state.bounding_box ? [this.state] : []
      this.geocodedTaxLots = this.geocodedRelated([this.state], 'bounding_box')
    } else {
      this.geocodedProperties = this.geocodedRelated([this.state], 'bounding_box')
      this.geocodedTaxLots = this.state.bounding_box ? [this.state] : []
    }
  }

  geocodedRelated(data: State[], field: string): State[] {
    const related: State[] = []

    for (const record of data) {
      if (record.related?.length) {
        related.push(...record.related.filter((r) => r[field]))
      }
    }

    // group by id
    const seen = new Set()
    return related.filter((item) => {
      if (seen.has(item.id)) return false
      seen.add(item.id)
      return true
    })
  }

  setGeocodedData() {
    this.geocodedData = this.state.long_lat ? [this.state] : []
    this.unGeocodedData = this.state.long_lat ? [] : [this.state]
    this.boundingBox = this.state.bounding_box.replace(/^SRID=\d+;/, '')
    this.centroid = this.state.centroid.replace(/^SRID=\d+;/, '')
  }

  buildLayers() {
    this.layers = {
      pointsLayer: { zIndex: 2, visible: 1 },
      buildingBBLayer: { zIndex: 3, visible: this.type === 'taxlots' ? 0 : 1 },
      buildingCentroidLayer: { zIndex: 4, visible: this.type === 'taxlots' ? 0 : 1 },
      taxlotBBLayer: { zIndex: 5, visible: this.type === 'taxlots' ? 1 : 0 },
      taxlotCentroidLayer: { zIndex: 6, visible: this.type === 'taxlots' ? 1 : 0 },
      baseLayer: { zIndex: 0, visible: 1 },
    }
  }

  setBaseLayer() {
    this.baseLayer = new TileLayer({
      source: new OSM(),
      zIndex: this.layers.baseLayer.zIndex,
    })
  }

  buildingBoundingBox() {
    const format = new WKT()
    const feature = format.readFeature(this.boundingBox, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    })

    feature.setProperties(this.state)
    return feature
  }

  buildingSources() {
    const features = [this.buildingBoundingBox()]
    return new VectorSource({ features })
  }

  // Define building UBID bounding box
  buildingBB() {
    const format = new WKT()

    const feature = format.readFeature(this.boundingBox, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    })
    feature.setProperties(this.state)
    return feature
  }

  // Define building UBID centroid box
  buildingCentroid() {
    const format = new WKT()

    const feature = format.readFeature(this.centroid, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    })

    feature.setProperties(this.state)
    return feature
  }

  buildingBBSources() {
    const features = [this.buildingBB()]
    return new VectorSource({ features })
  }

  buildingCentroidSources = () => {
    const features = [this.buildingCentroid()]
    return new VectorSource({ features })
  }

  // Define taxlot UBID bounding box
  taxlotBB() {
    const format = new WKT()

    const feature = format.readFeature(this.boundingBox, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    })

    feature.setProperties(this.state)
    return feature
  }

  // Define taxlot UBID centroid box
  taxlotCentroid() {
    const format = new WKT()

    const feature = format.readFeature(this.centroid, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    })
    feature.setProperties(this.state)
    return feature
  }

  taxlotBBSources() {
    const features = [this.taxlotBB()]
    return new VectorSource({ features })
  }

  taxlotCentroidSources() {
    const features = [this.taxlotCentroid()]
    return new VectorSource({ features })
  }

  setCluster() {
    this.clusterSource = new Cluster({
      source: this.buildingSources(),
      distance: 45,
    })
  }

  setStyles() {
    // style for building ubid bounding and centroid boxes
    this.buildingStyle = new Style({
      stroke: new Stroke({
        color: '#185189',
        width: 2,
      }),
    })

    // style for taxlot ubid bounding and centroid boxes
    this.taxlotStyle = new Style({
      stroke: new Stroke({
        color: '#10A0A0',
        width: 2,
      }),
    })
  }

  setLayers() {
    this.buildingBBLayer = new VectorLayer({
      source: this.buildingBBSources(),
      zIndex: this.layers.buildingBBLayer.zIndex,
      style: this.buildingStyle,
    })

    this.buildingCentroidLayer = new VectorLayer({
      source: this.buildingCentroidSources(),
      zIndex: this.layers.buildingCentroidLayer.zIndex,
      style: this.buildingStyle,
    })

    this.taxlotBBLayer = new VectorLayer({
      source: this.taxlotBBSources(),
      zIndex: this.layers.taxlotBBLayer.zIndex,
      style: this.taxlotStyle,
    })

    this.taxlotCentroidLayer = new VectorLayer({
      source: this.taxlotCentroidSources(),
      zIndex: this.layers.taxlotCentroidLayer.zIndex,
      style: this.taxlotStyle,
    })
  }

  renderMap() {
    let layers = []
    if (this.type === 'properties') {
      layers = [this.baseLayer, this.buildingBBLayer, this.buildingCentroidLayer]
    } else {
      layers = [this.baseLayer, this.taxlotBBLayer, this.taxlotCentroidLayer]
    }
    this.map = new Map({
      target: 'map',
      layers,
      controls: defaultControls({
        zoom: false,
        attribution: false,
        rotate: false,
      }),
    })
  }

  // Zoom and center based on provided points (none, all, or a subset)
  zoomCenter = (boundingBoxSource: VectorSource, extraViewOptions: Record<string, unknown> = {}) => {
    if (boundingBoxSource.isEmpty()) {
      // Default view with no points is the middle of US
      const emptyView = new View({
        center: fromLonLat([-99.066067, 39.390897]),
        zoom: 4.5,
      })
      this.map.setView(emptyView)
    } else {
      const extent = boundingBoxSource.getExtent()

      const viewOptions = {
        size: this.map.getSize(),
        padding: [50, 50, 50, 50],
        ...extraViewOptions,
      }
      this.map.getView().fit(extent, viewOptions)
    }
  }

  styleMap() {
    const viewport = this.map.getViewport()

    // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
    const frame = viewport.querySelector('.ol-viewport') as HTMLElement
    if (frame) {
      frame.style.border = '1px solid gray'
      frame.style.borderRadius = '3px'
    }
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
    const overlay = viewport.querySelector('.ol-overlaycontainer') as HTMLElement
    if (overlay) {
      overlay.style.display = 'none'
    }
  }
}
