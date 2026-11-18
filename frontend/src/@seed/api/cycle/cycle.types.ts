export type Cycle = {
  name: string;
  start: string;
  end: string;
  organization: number;
  user: number | null;
  id: number;
}

export type CyclesResponse = {
  status: string;
  cycles: Cycle[];
}

export type CycleResponse = {
  status: string;
  cycles: Cycle;
}
