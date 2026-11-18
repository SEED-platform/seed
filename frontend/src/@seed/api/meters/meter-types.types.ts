export type MeterWithUnits = {
  name: string;
  units: string[];
}

export type MeterTypeWithUnitsResponse = {
  energy: Record<string, string[]>;
  water: Record<string, string[]>;
}
