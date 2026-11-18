import type { AccessLevelInstance } from '@seed/api'

export type EditAccessLevelsData = {
  accessLevelNames: string[];
  organizationId: number;
}

export type CreateInstanceData = {
  accessLevelNames: string[];
  parentInstance: AccessLevelInstance;
  organizationId: number;
}

export type RenameInstanceData = {
  accessLevelNames: string[];
  accessLevelTree: AccessLevelInstance[];
  instance: AccessLevelInstance;
  organizationId: number;
}

export type DeleteInstanceData = {
  instance: AccessLevelInstance;
  organizationId: number;
  warnings: string[];
}

export type UploadInstancesData = {
  organizationId: number;
}
