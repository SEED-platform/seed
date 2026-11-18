export type Config = {
  action: (tab: string) => void;
  dense?: boolean;
  tabs: string[];
}
