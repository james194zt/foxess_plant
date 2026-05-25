import type { HomeAssistant, PlantConfig } from "./types";
import { stateNumber } from "./types";

export interface EnergyFlows {
  pvW: number;
  loadW: number;
  gridImportW: number;
  gridExportW: number;
  batteryW: number;
  batterySoc: number;
  batteryStatus: string;
}

export function readEnergyFlows(
  hass: HomeAssistant,
  plant: PlantConfig
): EnergyFlows {
  const map = plant.entity_map;
  const pvW = stateNumber(hass, map.pv_power);
  const loadW = Math.abs(stateNumber(hass, map.load_power));
  const gridImportW = stateNumber(hass, map.grid_import);
  const gridExportW = stateNumber(hass, map.grid_export);
  let batteryW = stateNumber(hass, map.battery_power);
  const statusEntity = map.battery_status;
  let batteryStatus = "Idle";
  if (statusEntity && hass.states[statusEntity]) {
    batteryStatus = hass.states[statusEntity].state;
  } else if (batteryW > 50) {
    batteryStatus = "Discharging";
  } else if (batteryW < -50) {
    batteryStatus = "Charging";
  }
  return {
    pvW: Math.max(0, pvW),
    loadW,
    gridImportW: Math.max(0, gridImportW),
    gridExportW: Math.max(0, gridExportW),
    batteryW,
    batterySoc: stateNumber(hass, map.battery_soc),
    batteryStatus,
  };
}

export interface FlowLine {
  id: string;
  active: boolean;
  reverse?: boolean;
  label?: string;
}

export function computeFlowLines(flows: EnergyFlows, threshold = 40): FlowLine[] {
  const lines: FlowLine[] = [];
  if (flows.pvW > threshold) {
    lines.push({ id: "solar-home", active: true, label: formatW(flows.pvW) });
  }
  if (flows.gridImportW > threshold) {
    lines.push({
      id: "grid-home",
      active: true,
      label: formatW(flows.gridImportW),
    });
  }
  if (flows.gridExportW > threshold) {
    lines.push({
      id: "home-grid",
      active: true,
      reverse: true,
      label: formatW(flows.gridExportW),
    });
  }
  if (flows.batteryW > threshold) {
    lines.push({
      id: "battery-home",
      active: true,
      label: formatW(flows.batteryW),
    });
  } else if (flows.batteryW < -threshold) {
    lines.push({
      id: "home-battery",
      active: true,
      label: formatW(Math.abs(flows.batteryW)),
    });
  }
  return lines;
}

function formatW(w: number): string {
  const kw = Math.abs(w) / 1000;
  return kw < 10 ? `${kw.toFixed(2)} kW` : `${kw.toFixed(1)} kW`;
}
