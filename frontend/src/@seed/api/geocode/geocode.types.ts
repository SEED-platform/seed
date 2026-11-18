export type ConfidenceSummary = {
  properties?: InventoryConfidenceSummary;
  taxlots?: InventoryConfidenceSummary;
}

export type InventoryConfidenceSummary = {
  census_geocoder: number;
  high_confidence: number;
  low_confidence: number;
  manual: number;
  missing_address_components: number;
  not_geocoded: number;
}

export type GeocodingColumns = {
  PropertyState: string[]; // column_name
  TaxLotState: string[];
}
