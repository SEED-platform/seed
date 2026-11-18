import type { Pagination } from 'app/modules/inventory'

export type DataLogger = {
  display_name: string;
  id: number;
  identifier: string;
  location_description: string;
  manufacturer_name: string;
  model_name: string;
  serial_number: string;
}

export type Sensor = {
  column_name: string;
  data_logger: string;
  data_logger_id: number;
  description: string;
  display_name: string;
  id: number;
  location_description: string;
  sensor_type: string;
  units: string;
}

export type SensorUsage = {
  column_defs: SensorReadingColumnDef[];
  pagination: Pagination;
  readings: SensorReading[];
}

export type SensorReadingColumnDef = {
  displayName: string;
  field: string;
  _filter_type: 'reading' | 'datetime';
}

export type SensorReading = {
  [key: string]: number | string;
  timestamp: string;
}

export type ReadingInterval = 'Exact' | 'Month' | 'Year'

export type SensorUsageRequestConfig = {
  interval?: string;
  showOnlyOccupiedReadings?: boolean;
  page?: number;
  per_page?: number;
  excluded_sensor_ids?: number[];
}
