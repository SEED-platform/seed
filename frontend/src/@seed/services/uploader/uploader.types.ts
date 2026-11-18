import type { ProgressResponse, Sensor } from '@seed/api'

export type ProgressBarObj = {
  message: unknown;
  progress: number;
  complete: boolean;
  statusMessage: string;
  progressLastUpdated: number | null;
  progressLastChecked: number | null;
  totalRecords?: number | null;
  completedRecords?: number | null;
  total?: number;
}

export type CheckProgressLoopParams = {
  progressKey: string;
  progressBarObj: ProgressBarObj;
  offset?: number;
  multiplier?: number;
  successFn?: (response: ProgressResponse) => void;
  failureFn?: () => void;
  subProgress?: boolean;
}

export type UpdateProgressBarObjParams = {
  data: ProgressResponse;
  offset: number;
  multiplier: number;
  progressBarObj: ProgressBarObj;
}

export type UploadResponse = {
  success: boolean;
  import_file_id?: number;
  message?: string;
}

export type SensorPreviewResponse = {
  proposed_imports: Sensor[];
}

export type SensorReadingPreview = { column_name: string; exists: boolean; num_readings: number }

export type GreenButtonMeterPreview = {
  proposed_imports: MeterImport[];
  validated_type_units: ValidatedTypeUnit[];
}

export type MeterImport = {
  cycles?: string;
  errors?: string;
  incoming: number;
  property_id: number;
  pm_property_id?: number;
  source_id: string;
  system_id: number;
  type: string;
  successfully_imported?: number;
}

export type ValidatedTypeUnit = {
  parsed_type: string;
  parsed_unit: string;
}

export type MeterPreviewResponse = {
  proposed_imports: MeterImport[];
  unlinkable_pm_ids: number[];
  validated_type_units: ValidatedTypeUnit[];
}

export type ExportDataType = 'csv' | 'xlsx' | 'geojson'
