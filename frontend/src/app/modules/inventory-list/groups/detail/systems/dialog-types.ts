import type { GroupSystem } from '@seed/api'

export type SystemDialogData = {
  action: 'create' | 'edit' | 'delete';
  orgId: number;
  groupId: number;
  system?: GroupSystem;
}

export type ServiceDialogData = {
  action: 'create' | 'edit' | 'delete';
  orgId: number;
  groupId: number;
  systemId: number;
  systemName: string;
  service?: { id: number; name: string; emission_factor: number | null };
}
