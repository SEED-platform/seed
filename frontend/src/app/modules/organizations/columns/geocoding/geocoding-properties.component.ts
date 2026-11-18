import { CdkDrag, CdkDropList } from '@angular/cdk/drag-drop'
import { NgTemplateOutlet } from '@angular/common'
import { ChangeDetectionStrategy, Component, type OnInit, ViewEncapsulation } from '@angular/core'
import { ReactiveFormsModule } from '@angular/forms'
import type { Observable } from 'rxjs'
import { takeUntil } from 'rxjs'
import type { Column } from '@seed/api'
import { SharedImports } from '@seed/directives'
import { MaterialImports } from '@seed/materials'
import { GeocodingComponent } from './geocoding.component'

@Component({
  selector: 'seed-organizations-column-geocoding-properties',
  templateUrl: './geocoding.component.html',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [SharedImports, CdkDropList, CdkDrag, MaterialImports, NgTemplateOutlet, ReactiveFormsModule],
})
export class GeocodingPropertiesComponent extends GeocodingComponent implements OnInit {
  type = 'PropertyState'

  ngOnInit(): void {
    this._columnService.propertyColumns$.pipe(takeUntil(this._unsubscribeAll$)).subscribe((columns) => {
      this.setColumns(columns)
    })
  }

  protected refreshColumns(organizationId: number): Observable<Column[]> {
    return this._columnService.getPropertyColumns(organizationId)
  }
}
