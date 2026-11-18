import { NgTemplateOutlet } from '@angular/common'
import { provideHttpClient } from '@angular/common/http'
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing'
import { NO_ERRORS_SCHEMA } from '@angular/core'
import type { ComponentFixture } from '@angular/core/testing'
import { TestBed } from '@angular/core/testing'
import { MatCheckbox } from '@angular/material/checkbox'
import { MatIconTestingModule } from '@angular/material/icon/testing'
import { By } from '@angular/platform-browser'
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router'
import type { Feature } from 'ol'
import VectorLayer from 'ol/layer/Vector'
import Map from 'ol/Map'
import VectorSource from 'ol/source/Vector'
import Style from 'ol/style/Style'
import View from 'ol/View'
import { EMPTY } from 'rxjs'
import { ColumnService, GroupsService, InventoryService, LabelService, OrganizationService, UserService } from '@seed/api'
import { MaterialImports } from '@seed/materials'
import { MapService } from '@seed/services/map'
import { MapComponent } from './map.component'

describe('MapComponent', () => {
  let component: MapComponent
  let fixture: ComponentFixture<MapComponent>
  let http: HttpTestingController

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MapComponent, MatIconTestingModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ type: 'properties' }) } } },
        { provide: Router, useValue: {} },
        { provide: ColumnService, useValue: {} },
        { provide: GroupsService, useValue: {} },
        { provide: InventoryService, useValue: {} },
        { provide: LabelService, useValue: {} },
        { provide: OrganizationService, useValue: {} },
        { provide: UserService, useValue: { currentUser$: EMPTY } },
      ],
    })
      .overrideComponent(MapComponent, {
        set: { imports: [NgTemplateOutlet, MaterialImports], schemas: [NO_ERRORS_SCHEMA] },
      })
      .compileComponents()

    fixture = TestBed.createComponent(MapComponent)
    component = fixture.componentInstance
    component.censusTractLayer = new VectorLayer({ source: new VectorSource() })
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    fixture.destroy()
    component.censusTractLayer.dispose()
    component.map?.dispose()
    http.verify()
  })

  for (const initiallyHighlighted of [true, false]) {
    it(`should immediately invalidate census tract styles when turning highlights ${initiallyHighlighted ? 'off' : 'on'}`, () => {
      component.highlightDACs = initiallyHighlighted
      const layer = component.censusTractLayer
      const source = layer.getSource()
      const revision = layer.getRevision()
      const onChange = jasmine.createSpy('onChange').and.callFake(() => {
        expect(component.highlightDACs).toBe(!initiallyHighlighted)
      })
      layer.on('change', onChange)

      component.toggleHighlightDACs()

      expect(component.highlightDACs).toBe(!initiallyHighlighted)
      expect(onChange).toHaveBeenCalledTimes(1)
      expect(layer.getRevision()).toBeGreaterThan(revision)
      expect(layer.getSource()).toBe(source)
    })
  }

  describe('initial census tract loading', () => {
    beforeEach(() => {
      component.geocodedProperties = []
      component.geocodedTaxlots = []
      component.map = new Map({
        view: new View({ center: [0, 0], zoom: 12 }),
        controls: [],
        interactions: [],
      })
      component.map.setSize([256, 256])
      spyOn(window, 'fetch').and.resolveTo(
        new Response(
          JSON.stringify({
            type: 'FeatureCollection',
            features: [
              { type: 'Feature', properties: { GEOID10: '01001020100' }, geometry: { type: 'Point', coordinates: [0, 0] } },
              { type: 'Feature', properties: { GEOID10: '01001020200' }, geometry: { type: 'Point', coordinates: [0, 1] } },
            ],
          }),
        ),
      )
    })

    for (const highlightEnabled of [true, false]) {
      it(`should load tract styles with highlights ${highlightEnabled ? 'enabled by default' : 'disabled while loading'}`, async () => {
        expect(component.highlightDACs).toBeTrue()
        const layersReady = jasmine.createSpy('layersReady')
        const service = TestBed.inject(MapService)
        const checkStatus = service.checkDisadvantagedStatus.bind(service) as MapService['checkDisadvantagedStatus']
        const statusRequested = new Promise<void>((resolve) => {
          spyOn(service, 'checkDisadvantagedStatus').and.callFake((tractIds) => {
            resolve()
            return checkStatus(tractIds)
          })
        })
        const loading = component.setLayers().then(layersReady)
        await statusRequested
        await new Promise<void>((resolve) => setTimeout(resolve, 0))

        const request = http.expectOne('/api/v3/eeej/filter_disadvantaged_tracts/')
        expect(request.request.body).toEqual({ tract_ids: ['01001020100', '01001020200'] })
        expect(layersReady).not.toHaveBeenCalled()

        if (!highlightEnabled) component.toggleHighlightDACs()
        request.flush({ status: 'success', disadvantaged: ['01001020100'] })
        await loading

        expect(layersReady).toHaveBeenCalledTimes(1)
        const layer = component.censusTractLayer
        const styleFunction = layer.getStyleFunction()
        for (const feature of layer.getSource().getFeatures() as Feature[]) {
          const style = styleFunction(feature, 1)
          expect(style).toBeInstanceOf(Style)
          if (!(style instanceof Style)) throw new Error('Expected a census tract style')
          const shouldHighlight = highlightEnabled && feature.get('GEOID10') === '01001020100'
          expect(style.getFill()?.getColor()).toBe(shouldHighlight ? 'rgba(69, 130, 155, 0.4)' : undefined)
          expect(style.getStroke()).toBeTruthy()
        }
      })
    }
  })

  it('should mute the entire highlight control when census tracts are hidden and restore it when shown', async () => {
    component.groupId = 1
    component.data = [
      {
        id: 1,
        bounding_box: '',
        centroid: '',
        derived_data: {},
        extra_data: {},
        files: [],
        labels: [],
        measures: [],
        scenarios: [],
      },
    ]
    component.geocodedProperties = []
    component.geocodedTaxlots = []
    await component.setLayers()
    component.map = new Map({ layers: [component.censusTractLayer], controls: [], interactions: [] })
    fixture.detectChanges()

    const highlightControl = fixture.debugElement
      .queryAll(By.directive(MatCheckbox))
      .find((element) => (element.nativeElement as HTMLElement).textContent.includes('Highlight DACs'))
    expect(highlightControl).toBeDefined()
    if (!highlightControl) throw new Error('Expected the highlight control')
    const checkbox = highlightControl.injector.get(MatCheckbox)
    const element = highlightControl.nativeElement as HTMLElement

    expect(checkbox.disabled).toBeFalse()
    expect(element.classList.contains('opacity-40')).toBeFalse()

    component.toggleLayer('censusTractLayer', false)
    fixture.detectChanges()

    expect(checkbox.disabled).toBeTrue()
    expect(checkbox.checked).toBeTrue()
    expect(element.querySelector('input')?.disabled).toBeTrue()
    expect(element.classList.contains('opacity-40')).toBeTrue()

    component.toggleLayer('censusTractLayer', true)
    fixture.detectChanges()

    expect(checkbox.disabled).toBeFalse()
    expect(checkbox.checked).toBeTrue()
    expect(element.classList.contains('opacity-40')).toBeFalse()
  })
})
