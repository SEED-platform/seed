import { TestBed } from '@angular/core/testing'
import { MAT_DIALOG_DATA, MatDialog, MatDialogRef } from '@angular/material/dialog'
import { EMPTY, of } from 'rxjs'
import type { ProgressResponse } from '@seed/api'
import { DataQualityService } from '@seed/api'
import { UploaderService } from '@seed/services/uploader/uploader.service'
import type { CheckProgressLoopParams } from '@seed/services/uploader/uploader.types'
import { DQCResultsModalComponent } from './results-modal.component'
import { DQCStartModalComponent } from './start-modal.component'

describe('DQCStartModalComponent', () => {
  it('forwards the goal ID and uses the completed run ID to load results', async () => {
    const startCheck = jasmine.createSpy('startDataQualityCheckForOrg').and.returnValue(of({ progress_key: 'progress' }))
    const progressResponse: ProgressResponse = {
      func_name: 'check_data',
      message: null,
      progress: 100,
      progress_key: 'progress',
      stacktrace: null,
      status: 'success',
      status_message: '',
      summary: null,
      total: 5,
      unique_id: 81203,
    }
    const openDialog = jasmine.createSpy('open')
    const checkProgressLoop = jasmine.createSpy('checkProgressLoop').and.callFake((params: CheckProgressLoopParams) => {
      params.successFn?.(progressResponse)
      return EMPTY
    })
    await TestBed.configureTestingModule({
      imports: [DQCStartModalComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { orgId: 1, type: 'properties', viewIds: [], goalId: 42 } },
        { provide: MatDialog, useValue: { open: openDialog } },
        { provide: MatDialogRef, useValue: { close: jasmine.createSpy('close') } },
        { provide: DataQualityService, useValue: { startDataQualityCheckForOrg: startCheck } },
        { provide: UploaderService, useValue: { defaultProgressBarObj: {}, checkProgressLoop } },
      ],
    })
      .overrideComponent(DQCStartModalComponent, { set: { template: '', imports: [] } })
      .compileComponents()

    const fixture = TestBed.createComponent(DQCStartModalComponent)
    fixture.detectChanges()

    expect(startCheck).toHaveBeenCalledWith(1, [], [], 42)
    expect(openDialog).toHaveBeenCalledWith(DQCResultsModalComponent, {
      width: '50rem',
      data: { orgId: 1, dqcId: 81203 },
    })
    fixture.destroy()
  })
})
