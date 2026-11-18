export type UniformatCategory = {
  category: string;
  parent: string | null;
}

export type UniformatLookup = Record<string, UniformatCategory>
