import { provideZoneChangeDetection } from '@angular/core'
import { bootstrapApplication } from '@angular/platform-browser'
import { AppComponent } from 'app/app.component'
import { appConfig } from 'app/app.config'
import 'app/ag-grid-modules'
import 'app/chartjs-setup'

bootstrapApplication(AppComponent, { ...appConfig, providers: [provideZoneChangeDetection(), ...appConfig.providers] }).catch(
  (err: unknown) => {
    console.error(err)
  },
)
