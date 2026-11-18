import type { OrganizationUserSettings } from '../organization'

export type UserRole = 'viewer' | 'member' | 'owner'

export type CurrentUser = {
  first_name: string;
  last_name: string;
  email: string;
  username: string;
  api_key: string;
  is_superuser: boolean;
  id: number;
  pk: number;
  two_factor_method: 'disabled' | 'email' | 'token';
  org_id: number;
  org_name: string;
  org_role: UserRole;
  ali_name: string;
  ali_id: number;
  is_ali_root: boolean;
  is_ali_leaf: boolean;
  org_user_id: number;
  settings: OrganizationUserSettings;
}

export type UserBrief = {
  user_id: number;
  email: string;
}

export type UserUpdateRequest = {
  first_name: string;
  last_name: string;
  email: string;
}

export type CreateUserRequest = {
  first_name: string;
  last_name: string;
  email: string;
  org_name: string;
  role: UserRole;
  access_level_instance_id: number;
}

export type PasswordUpdateRequest = {
  current_password: string;
  password_1: string;
  password_2: string;
}

export type SetDefaultOrganizationResponse = {
  status: string;
  user: {
    id: number;
    access_level_instance: {
      id: number;
      name: string;
    };
  };
}

export type GenerateApiKeyResponse = {
  status: string;
  api_key: string;
}

export type PasswordUpdateResponse = {
  status: string;
}

export type MemberForm = {
  first_name: string;
  last_name: string;
  email: string;
  access_level: string;
  access_level_instance_id: number;
  role: UserRole;
}

export type Action = 'can_invite_member' | 'can_remove_member' | 'requires_owner' | 'requires_member' | 'requires_superuser'

export type UserAuth = Partial<Record<Action, boolean>>

export type UserAuthResponse = {
  auth: UserAuth;
  status: boolean;
}
