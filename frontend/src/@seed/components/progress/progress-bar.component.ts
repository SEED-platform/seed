import { CommonModule } from '@angular/common'
import { ChangeDetectionStrategy, Component, Input } from '@angular/core'
import { MaterialImports } from '@seed/materials'

@Component({
  selector: 'seed-progress-bar',
  templateUrl: './progress-bar.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [CommonModule, MaterialImports],
})
export class ProgressBarComponent {
  @Input() total: number
  @Input() progress: number
  @Input() title: string
  @Input() outline = false
  @Input() showSubProgress? = false
  @Input() subProgress?: number
  @Input() subTotal?: number
  @Input() subTitle?: string

  get percent() {
    return (this.progress / this.total) * 100
  }

  get progressString() {
    return this.getProgressString(this.total, this.progress)
  }

  get subProgressString() {
    if (!this.showSubProgress) return
    return this.getProgressString(this.subTotal, this.subProgress)
  }

  get subPercent() {
    return this.subTotal ? (this.subProgress / this.subTotal) * 100 : undefined
  }

  getProgressMode(progress) {
    return progress ? 'determinate' : 'indeterminate'
  }

  getProgressString(totalFloat: number, progressFloat: number) {
    const total = Math.round(totalFloat)
    const progress = Math.round(progressFloat)
    const suffix = total === 100 ? '%' : `/ ${total}`
    return `${progress} ${suffix}`
  }
}
