export interface HassEntity {
  state: string;
  attributes: Record<string, unknown>;
  last_changed?: string;
}

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  callService: (
    domain: string,
    service: string,
    data?: Record<string, unknown>
  ) => Promise<void>;
  connection: {
    sendMessagePromise: (msg: Record<string, unknown>) => Promise<unknown>;
  };
  formatEntityState?: (stateObj: HassEntity, state?: string) => string;
}

export interface PlantConfig {
  entry_id: string;
  title: string;
  inverter: string;
  entity_map: Record<string, string>;
}

export interface PanelConfig {
  plants: PlantConfig[];
}

export interface PanelInfo {
  config: PanelConfig;
}

export type PanelView = "overview" | "device" | "settings";
export type SettingsView = "main" | "storm";

export function stateNumber(hass: HomeAssistant, entityId?: string): number {
  if (!entityId) return 0;
  const st = hass.states[entityId];
  if (!st || st.state === "unavailable" || st.state === "unknown") return 0;
  const n = parseFloat(st.state);
  return Number.isFinite(n) ? n : 0;
}

export function stateString(hass: HomeAssistant, entityId?: string): string {
  if (!entityId) return "—";
  const st = hass.states[entityId];
  if (!st) return "—";
  return st.state;
}

export function formatKw(watts: number, decimals = 2): string {
  const kw = Math.abs(watts) / 1000;
  if (kw >= 10) return `${kw.toFixed(1)} kW`;
  return `${kw.toFixed(decimals)} kW`;
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export async function fetchPlantState(
  hass: HomeAssistant,
  plantId: string
): Promise<Record<string, unknown>> {
  return (await hass.connection.sendMessagePromise({
    type: "foxess_plant/plant_state",
    plant_id: plantId,
  })) as Record<string, unknown>;
}
