import { Chart, registerables } from 'chart.js'
import annotationPlugin from 'chartjs-plugin-annotation'
import zoomPlugin from 'chartjs-plugin-zoom'

Chart.register(...registerables)
Chart.register(annotationPlugin)
Chart.register(zoomPlugin)

// Optional background plugin for charts that need a non-transparent export background
Chart.register({
  id: 'customCanvasBackgroundColor',
  beforeDraw(chart, _args, options) {
    let color: string | undefined

    if (typeof options === 'string') {
      color = options
    } else if (typeof options?.color === 'string') {
      color = options.color
    }

    if (!color) {
      return
    }

    const { ctx } = chart
    ctx.save()
    ctx.globalCompositeOperation = 'destination-over'
    ctx.fillStyle = color
    ctx.fillRect(0, 0, chart.width, chart.height)
    ctx.restore()
  },
})
