/**
 * EVO user manual §10.1 fault descriptions & solutions (pp. 54–57) and BMS state decode (p. 58–59).
 * @module fox-alarm-guide
 */

import { tl } from "./fox-i18n.js";

/** @typedef {{ manualName: string, description: string, solutions: string[], bmsRelated?: boolean }} FoxAlarmGuideEntry */

/** EVO manual alarm list — keyed by manual fault short name. */
export const FOX_EVO_MANUAL_FAULTS = {
  "Grid Lost Fault": {
    description: tl("alerts.grid_is_lost"),
    solutions: [
      tl("alerts.system_will_reconnect_if_the_utility"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Grid Volt Fault": {
    description: tl("alerts.grid_voltage_out_of_range"),
    solutions: [
      tl("alerts.system_will_reconnect_if_the_utility"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Grid Freq Fault": {
    description: tl("alerts.grid_frequency_out_of_range"),
    solutions: [
      tl("alerts.system_will_reconnect_if_the_utility"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "10min Volt Fault": {
    description: tl("alerts.the_grid_voltage_is_out_of"),
    solutions: [
      tl("alerts.system_will_reconnect_if_the_utility"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "SW Inv Cur Fault": {
    description: tl("alerts.output_current_high_detected_by_software"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "DCI Fault": {
    description: tl("alerts.dc_component_is_out_of_limit"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "HW Inv Cur Fault": {
    description: tl("alerts.output_current_high_detected_by_hardware"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "SW Bus Vol Fault": {
    description: tl("alerts.bus_voltage_out_of_range_detected"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Bat Volt Fault": {
    description: tl("alerts.battery_voltage_fault"),
    solutions: [
      tl("alerts.check_if_the_battery_input_voltage"),
      tl("alerts.or_seek_help_from_us"),
    ],
    bmsRelated: true,
  },
  "SW Bat Cur Fault": {
    description: tl("alerts.battery_current_high_detected_by_software"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
    bmsRelated: true,
  },
  "Iso Fault": {
    description: tl("alerts.the_isolation_has_failed"),
    solutions: [
      tl("alerts.please_check_if_the_insulation_of"),
      tl("alerts.wait_for_a_while_to_check"),
      tl("alerts.or_seek_for_help_from_us"),
    ],
  },
  "Res Cur Fault": {
    description: tl("alerts.the_residual_current_is_high"),
    solutions: [
      tl("alerts.please_check_if_the_insulation_of"),
      tl("alerts.wait_for_a_while_to_check"),
      tl("alerts.or_seek_for_help_from_us"),
    ],
  },
  "Pv Volt Fault": {
    description: tl("alerts.pv_voltage_out_of_range"),
    solutions: [tl("alerts.please_check_the_output_voltage_of"), tl("alerts.or_seek_for_help_from_us")],
  },
  "SW Pv Cur Fault": {
    description: tl("alerts.pv_input_current_high_detected_by"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Temp Fault": {
    description: tl("alerts.the_inverter_temperature_is_high"),
    solutions: [
      tl("alerts.please_check_the_environment_temperature"),
      tl("alerts.wait_for_a_while_to_check"),
      tl("alerts.or_seek_for_help_from_us"),
    ],
  },
  "Ground Fault": {
    description: tl("alerts.the_ground_connection_has_failed"),
    solutions: [
      tl("alerts.check_the_voltage_of_neutral_and"),
      tl("alerts.check_ac_wiring"),
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Over Load Fault": {
    description: tl("alerts.overload_in_on_grid_mode"),
    solutions: [tl("alerts.please_check_if_the_load_power"), tl("alerts.or_seek_for_help_from_us")],
  },
  "Eps Over Load": {
    description: tl("alerts.overload_in_off_grid_mode"),
    solutions: [tl("alerts.please_check_if_the_eps_load"), tl("alerts.or_seek_for_help_from_us")],
  },
  "Bat Power Low": {
    description: tl("alerts.the_battery_power_is_low"),
    solutions: [tl("alerts.wait_for_the_battery_to_be"), tl("alerts.or_seek_for_help_from_us")],
    bmsRelated: true,
  },
  "HW Bus Vol Fault": {
    description: tl("alerts.bus_voltage_out_of_range_detected_2"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "HW Pv Cur Fault": {
    description: tl("alerts.pv_input_current_high_detected_by_2"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "HW Bat Cur Fault": {
    description: tl("alerts.battery_current_high_detected_by_hardware"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
    bmsRelated: true,
  },
  "SCI Fault": {
    description: tl("alerts.the_communication_between_master_and_manager"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "MDSP SPI Fault": {
    description: tl("alerts.the_communication_between_master_and_slave"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "MDSP Smpl Fault": {
    description: tl("alerts.the_master_sample_detection_circuit_has"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Res Cur HW Fault": {
    description: tl("alerts.residual_current_detection_device_has_failed"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Inv EEPROM Fault": {
    description: tl("alerts.the_inverter_eeprom_is_faulty"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "PvCon Dir Fault": {
    description: tl("alerts.the_pv_connection_is_reversed"),
    solutions: [
      tl("alerts.check_if_the_positive_pole_and"),
      tl("alerts.or_seek_help_from_us"),
    ],
  },
  "Bat Relay Open": {
    description: tl("alerts.the_battery_relay_keeps_open"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
    bmsRelated: true,
  },
  "Bat Relay Short Circuit": {
    description: tl("alerts.the_battery_relay_keeps_closed"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
    bmsRelated: true,
  },
  "Bat Buck Fault": {
    description: tl("alerts.the_battery_buck_circuit_mosfet_has"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
    bmsRelated: true,
  },
  "Bat Boost Fault": {
    description: tl("alerts.the_battery_boost_circuit_mosfet_has"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
    bmsRelated: true,
  },
  "Eps Relay Fault": {
    description: tl("alerts.the_eps_relay_has_failed"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "BatCon Dir Fault": {
    description: tl("alerts.the_battery_connection_is_reversed"),
    solutions: [
      tl("alerts.check_if_the_positive_pole_and_2"),
      tl("alerts.or_seek_help_from_us"),
    ],
    bmsRelated: true,
  },
  "Main Relay Open": {
    description: tl("alerts.the_grid_relay_keeps_open"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "S1 Close Fault": {
    description: tl("alerts.the_grid_relay_s1_keeps_closed"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "S2 Close Fault": {
    description: tl("alerts.the_grid_relay_s2_keeps_closed"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "M1 Close Fault": {
    description: tl("alerts.the_grid_relay_m1_keeps_closed"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "M2 Close Fault": {
    description: tl("alerts.the_grid_relay_m2_keeps_closed"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "GridV Cons Fault": {
    description: tl("alerts.grid_voltage_sample_values_between_master"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "GridF Cons Fault": {
    description: tl("alerts.grid_frequency_sample_values_between_master"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Dci Cons Fault": {
    description: tl("alerts.dci_sample_values_between_master_and"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Rc Cons Fault": {
    description: tl("alerts.residual_current_sample_values_between_master"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "RDSP SPI Fault": {
    description: tl("alerts.the_communication_between_master_and_slave"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "RDSP Smpl Fault": {
    description: tl("alerts.the_slave_sample_detection_circuit_has"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "ARM EEPROM Fault": {
    description: tl("alerts.the_manager_eeprom_is_faulty"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "Meter Lost Fault": {
    description: tl("alerts.communication_between_the_meter_and_inverter"),
    solutions: [
      tl("alerts.check_if_the_communication_cable_between"),
    ],
  },
  "DC arc fault": {
    description: tl("alerts.dc_arc_fault_detected_requires_arc"),
    solutions: [
      tl("alerts.disconnect_pv_grid_and_battery_then"),
      tl("alerts.inspect_pv_wiring_and_connectors_for"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  Islanding: {
    description: tl("alerts.islanding_condition_detected"),
    solutions: [
      tl("alerts.system_will_reconnect_if_the_utility"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
  },
  "External fan fault": {
    description: tl("alerts.external_cooling_fan_fault"),
    solutions: [
      tl("alerts.check_that_the_inverter_ventilation_path"),
      tl("alerts.wait_for_a_while_to_check"),
      tl("alerts.or_seek_for_help_from_us"),
    ],
  },
  "BMS lost": {
    description: tl("alerts.communication_between_the_inverter_and_bms"),
    solutions: [
      tl("alerts.check_bms_communication_cables_and_battery"),
      tl("alerts.review_active_bms_fault_states_below"),
      tl("alerts.or_seek_help_from_us_if"),
    ],
    bmsRelated: true,
  },
};

/** Modbus / Fox app alarm label → EVO manual fault key. */
export const FOX_ALARM_TO_MANUAL = {
  "PV Over-voltage": tl("alerts.pv_volt_fault"),
  "DC arc fault": tl("alerts.dc_arc_fault"),
  "String reverse connection": tl("alerts.pvcon_dir_fault"),
  "Grid power outage": tl("alerts.grid_lost_fault"),
  "Abnormal grid voltage": tl("alerts.grid_volt_fault"),
  "Abnormal grid frequency": tl("alerts.grid_freq_fault"),
  "Output overcurrent": tl("alerts.sw_inv_cur_fault"),
  "Output DC component too large": tl("alerts.dci_fault"),
  "Residual current": tl("alerts.res_cur_fault"),
  "Grounding fault": tl("alerts.ground_fault"),
  "Low insulation resistance": tl("alerts.iso_fault"),
  "Inverter overtemperature": tl("alerts.temp_fault"),
  "Energy storage equipment abnormal": tl("alerts.bat_volt_fault"),
  Islanding: tl("alerts.islanding"),
  "Off-grid output overload": tl("alerts.eps_over_load"),
  "External fan fault": tl("alerts.external_fan_fault"),
  "Energy storage reverse connection": tl("alerts.batcon_dir_fault"),
  "Meter lost": tl("alerts.meter_lost_fault"),
  "BMS lost": tl("alerts.bms_lost"),
  "Grid Lost Fault": tl("alerts.grid_lost_fault"),
  "Grid Voltage Fault": tl("alerts.grid_volt_fault"),
  "Grid Frequency Fault": tl("alerts.grid_freq_fault"),
  "Output Over-current Fault": tl("alerts.sw_inv_cur_fault"),
  "Output DC Over-current Fault": tl("alerts.dci_fault"),
  "Residual Current Consistency Fault": tl("alerts.res_cur_fault"),
  "Ground Connection Fault": tl("alerts.ground_fault"),
  "Low Insulation Resistante Fault": tl("alerts.iso_fault"),
  "Inverter Over-temperature Fault": tl("alerts.temp_fault"),
  "Energy Storage Equipment Abnormal Fault": tl("alerts.bat_volt_fault"),
  "Isolated Island Fault": tl("alerts.islanding"),
  "Off-grid Output Overload Fault": tl("alerts.eps_over_load"),
  "External Fan Fault": tl("alerts.external_fan_fault"),
  "Energy Storage Reverse Connection Fault": tl("alerts.batcon_dir_fault"),
  "Meter Lost Fault": tl("alerts.meter_lost_fault"),
  "BMS Lost Fault": tl("alerts.bms_lost"),
};

/** BMS fault bitfields BS1–BS6 (EVO user manual p. 58–59). Index = bit 0–7. */
export const FOX_BMS_FAULT_BITS = [
  [
    "Communication fault with PCS (EXT COM)",
    "Internal communication fault (INT COM)",
    "Over voltage fault (OV)",
    "Under voltage fault (UV)",
    "Charge over current (OCC)",
    "Discharge over current (OCD)",
    "Over temperature fault (OT)",
    "Under temperature (UT)",
  ],
  [
    "Cell imbalance alarm (CB)",
    "Hardware Protect",
    null,
    "BMS Other Fault",
    "Voltage Sensor Fault",
    "Temperature Sensor Fault",
    "Current Sensor Fault",
    "Relay Fault",
  ],
  [
    "Inconsistent cell capacity fault (BMS_Typc_Unmatch)",
    null,
    null,
    null,
    null,
    "Unanswered charging request (BMS_MR_Unmatch)",
    null,
    null,
  ],
  [null, null, null, null, "Pre-charge fault", null, null, null],
  [
    "Relay drive circuit failure (Actor_Fault)",
    "SOH_LOW",
    null,
    null,
    "Single cell 0V fault (SUV)",
    "Extreme overvoltage fault (CellVolt R&H Invalid)",
    "Cell Temperature High Invalid",
    "Balance Temperature High",
  ],
  [
    "Precharge resistor overtemperature (PreChg_Restemperature High)",
    "Hardware overcurrent fault (short_current)",
    "AFE Communication Fault",
    "AFE Fault (AFE UT/OT/UV/OV)",
    "IVU Communication fault",
    null,
    "Module addressing fault",
    null,
  ],
];

const FOX_BMS_E_CODES = ["E01", "E02", "E04", "E08", "E10", "E20", "E40", "E80"];

/**
 * Alert name for one BMS fault bit, using the EVO manual's table, e.g. index 1 bit 0 ->
 * "Battery BS1 E01: Communication fault with PCS (EXT COM)". Bits the manual doesn't name keep their raw bit.
 * Keep in step with BMS_FAULT_BITS in alert_log.py.
 * @param {number} index BS register 1-6 (37626-37631)
 * @param {number} bit 0-15
 */

/**
 * The name shown for an alarm. Alarm names stay English inside — they come from foxess_modbus and from
 * the integration's alert log, and raised / cleared events are matched by name — so the known ones are
 * only translated here, where they are shown. Unknown names are returned unchanged.
 */
export function alarmDisplayName(name) {
  const text = String(name ?? "");
  const bms = /^Battery BS(\d+) (E\d+): (.+)$/.exec(text);
  if (bms) {
    const label = bmsBitDisplayName(bms[3]);
    return label === bms[3] ? text : tl("alarm_bms.fault_name", { index: bms[1], code: bms[2], label });
  }
  const labels = {
    "PV Over-voltage": tl("alarm_name.pv_over_voltage"),
    "DC arc fault": tl("alarm_name.dc_arc_fault"),
    "String reverse connection": tl("alarm_name.string_reverse_connection"),
    "Grid power outage": tl("alarm_name.grid_power_outage"),
    "Abnormal grid voltage": tl("alarm_name.abnormal_grid_voltage"),
    "Abnormal grid frequency": tl("alarm_name.abnormal_grid_frequency"),
    "Output overcurrent": tl("alarm_name.output_overcurrent"),
    "Output DC component too large": tl("alarm_name.output_dc_component_too_large"),
    "Residual current": tl("alarm_name.residual_current"),
    "Grounding fault": tl("alarm_name.grounding_fault"),
    "Low insulation resistance": tl("alarm_name.low_insulation_resistance"),
    "Inverter overtemperature": tl("alarm_name.inverter_overtemperature"),
    "Energy storage equipment abnormal": tl("alarm_name.energy_storage_equipment_abnormal"),
    "Islanding": tl("alarm_name.islanding"),
    "Off-grid output overload": tl("alarm_name.off_grid_output_overload"),
    "External fan fault": tl("alarm_name.external_fan_fault"),
    "Energy storage reverse connection": tl("alarm_name.energy_storage_reverse_connection"),
    "Meter lost": tl("alarm_name.meter_lost"),
    "BMS lost": tl("alarm_name.bms_lost"),
    "Grid Lost Fault": tl("alarm_name.grid_lost_fault"),
    "Grid Voltage Fault": tl("alarm_name.grid_voltage_fault"),
    "Grid Frequency Fault": tl("alarm_name.grid_frequency_fault"),
    "Output Over-current Fault": tl("alarm_name.output_over_current_fault"),
    "Output DC Over-current Fault": tl("alarm_name.output_dc_over_current_fault"),
    "Residual Current Consistency Fault": tl("alarm_name.residual_current_consistency_fault"),
    "Ground Connection Fault": tl("alarm_name.ground_connection_fault"),
    "Low Insulation Resistante Fault": tl("alarm_name.low_insulation_resistante_fault"),
    "Inverter Over-temperature Fault": tl("alarm_name.inverter_over_temperature_fault"),
    "Energy Storage Equipment Abnormal Fault": tl("alarm_name.energy_storage_equipment_abnormal_fault"),
    "Isolated Island Fault": tl("alarm_name.isolated_island_fault"),
    "Off-grid Output Overload Fault": tl("alarm_name.off_grid_output_overload_fault"),
    "External Fan Fault": tl("alarm_name.external_fan_fault_2"),
    "Energy Storage Reverse Connection Fault": tl("alarm_name.energy_storage_reverse_connection_fault"),
    "Meter Lost Fault": tl("alarm_name.meter_lost_fault"),
    "BMS Lost Fault": tl("alarm_name.bms_lost_fault"),
    "Inverter not responding (Modbus)": tl("alarm_name.inverter_not_responding_modbus"),
  };
  return labels[text] ?? text;
}

/** The shown text of one BMS fault bit (FOX_BMS_FAULT_BITS stays English, like the backend's table). */
export function bmsBitDisplayName(label) {
  const labels = {
    "Communication fault with PCS (EXT COM)": tl("alarm_bms.communication_fault_with_pcs_ext_com"),
    "Internal communication fault (INT COM)": tl("alarm_bms.internal_communication_fault_int_com"),
    "Over voltage fault (OV)": tl("alarm_bms.over_voltage_fault_ov"),
    "Under voltage fault (UV)": tl("alarm_bms.under_voltage_fault_uv"),
    "Charge over current (OCC)": tl("alarm_bms.charge_over_current_occ"),
    "Discharge over current (OCD)": tl("alarm_bms.discharge_over_current_ocd"),
    "Over temperature fault (OT)": tl("alarm_bms.over_temperature_fault_ot"),
    "Under temperature (UT)": tl("alarm_bms.under_temperature_ut"),
    "Cell imbalance alarm (CB)": tl("alarm_bms.cell_imbalance_alarm_cb"),
    "Hardware Protect": tl("alarm_bms.hardware_protect"),
    "BMS Other Fault": tl("alarm_bms.bms_other_fault"),
    "Voltage Sensor Fault": tl("alarm_bms.voltage_sensor_fault"),
    "Temperature Sensor Fault": tl("alarm_bms.temperature_sensor_fault"),
    "Current Sensor Fault": tl("alarm_bms.current_sensor_fault"),
    "Relay Fault": tl("alarm_bms.relay_fault"),
    "Inconsistent cell capacity fault (BMS_Typc_Unmatch)": tl("alarm_bms.inconsistent_cell_capacity_fault_bms_typc_unmatc"),
    "Unanswered charging request (BMS_MR_Unmatch)": tl("alarm_bms.unanswered_charging_request_bms_mr_unmatch"),
    "Pre-charge fault": tl("alarm_bms.pre_charge_fault"),
    "Relay drive circuit failure (Actor_Fault)": tl("alarm_bms.relay_drive_circuit_failure_actor_fault"),
    "SOH_LOW": tl("alarm_bms.soh_low"),
    "Single cell 0V fault (SUV)": tl("alarm_bms.single_cell_0v_fault_suv"),
    "Extreme overvoltage fault (CellVolt R&H Invalid)": tl("alarm_bms.extreme_overvoltage_fault_cellvolt_r_h_invalid"),
    "Cell Temperature High Invalid": tl("alarm_bms.cell_temperature_high_invalid"),
    "Balance Temperature High": tl("alarm_bms.balance_temperature_high"),
    "Precharge resistor overtemperature (PreChg_Restemperature High)": tl("alarm_bms.precharge_resistor_overtemperature_prechg_restem"),
    "Hardware overcurrent fault (short_current)": tl("alarm_bms.hardware_overcurrent_fault_short_current"),
    "AFE Communication Fault": tl("alarm_bms.afe_communication_fault"),
    "AFE Fault (AFE UT/OT/UV/OV)": tl("alarm_bms.afe_fault_afe_ut_ot_uv_ov"),
    "IVU Communication fault": tl("alarm_bms.ivu_communication_fault"),
    "Module addressing fault": tl("alarm_bms.module_addressing_fault"),
  };
  return labels[label] ?? label;
}

export function bmsFaultLabel(index, bit) {
  const label = FOX_BMS_FAULT_BITS[index - 1]?.[bit];
  if (label) return tl("alerts.battery_bs_index_value_label", { index, value: FOX_BMS_E_CODES[bit], label });
  return tl("alerts.battery_bs_index_bit_bit_0x", { index, bit, value: (1 << bit).toString(16).padStart(4, "0") });
}

/**
 * EVO manual §10.2 troubleshooting procedure, used as the solutions for faults the §10.1 Alarm
 * List doesn't give a specific fix for (the BMS State bits, and any unrecognised alarm). This is
 * the manual's real guidance — so we show it inline instead of telling the user to find the PDF.
 */
const FOX_MANUAL_GENERIC_SOLUTIONS = [
  tl("alerts.record_the_fault_and_the_time"),
  tl("alerts.check_the_inverter_is_in_a"),
  tl("alerts.contact_foxess_customer_service_with_your"),
];

/**
 * Plain-language descriptions for the BMS State fault bits. The EVO manual (§10.1, p.58–59) names
 * these bits but gives no per-bit solution, so we describe the condition and apply §10.2. Keyed by
 * the manual's exact fault phrase (as produced by {@link bmsFaultLabel}).
 */
export const FOX_BMS_FAULT_DESCRIPTIONS = {
  "Over voltage fault (OV)":
    tl("alerts.a_battery_voltage_rose_above_the"),
  "Under voltage fault (UV)":
    tl("alerts.a_battery_voltage_dropped_below_the"),
  "Charge over current (OCC)":
    tl("alerts.the_battery_was_being_charged_faster"),
  "Discharge over current (OCD)":
    tl("alerts.the_battery_was_being_drained_faster"),
  "Over temperature fault (OT)":
    tl("alerts.the_battery_got_too_warm_so"),
  "Under temperature (UT)":
    tl("alerts.the_battery_got_too_cold_so"),
};

const FOX_BMS_LABEL_RE = /^Battery (BS[1-6])\s*(?:E[0-9A-Fa-f]{2}:)?\s*(.*)$/;

/**
 * Guide entry for a decoded BMS State alarm (e.g. "Battery BS1 E10: Charge over current (OCC)" or
 * an unnamed "Battery BS1 bit 11 (0x0800)"). Returns null if the name isn't a BMS fault label.
 * @param {string} alarmName
 * @returns {FoxAlarmGuideEntry | null}
 */
function bmsGuideEntry(alarmName) {
  const m = FOX_BMS_LABEL_RE.exec(alarmName);
  if (!m) return null;
  const [, bs, faultName] = m;
  const description =
    FOX_BMS_FAULT_DESCRIPTIONS[faultName] ||
    tl("alerts.the_battery_reported_a_protection_fault", { faultName });
  return {
    manualName: `${faultName || alarmName} — battery ${bs}`,
    description,
    solutions: [
      tl("alerts.this_is_a_safety_cut_out"),
      ...FOX_MANUAL_GENERIC_SOLUTIONS,
    ],
    bmsRelated: true,
  };
}

/**
 * @param {string} alarmName
 * @returns {FoxAlarmGuideEntry}
 */
export function foxAlarmGuideEntry(alarmName) {
  const manualKey = FOX_ALARM_TO_MANUAL[alarmName] || alarmName;
  const manual = FOX_EVO_MANUAL_FAULTS[manualKey];
  if (manual) {
    return {
      manualName: manualKey,
      description: manual.description,
      solutions: manual.solutions,
      bmsRelated: Boolean(manual.bmsRelated),
    };
  }
  const bms = bmsGuideEntry(alarmName);
  if (bms) return bms;
  return {
    manualName: alarmName,
    description: tl("alerts.this_warning_doesn_t_have_a"),
    solutions: FOX_MANUAL_GENERIC_SOLUTIONS,
    bmsRelated: /bms|battery|energy storage/i.test(alarmName),
  };
}

/**
 * @param {Record<string, unknown>} hass
 * @param {Record<string, string>} map
 * @returns {{ register: string, code: string, label: string }[]}
 */
export function decodeBmsFaultRegisters(hass, map) {
  const active = [];
  for (let i = 1; i <= 6; i += 1) {
    const key = `bms_fault_${i}_raw`;
    const entityId = map[key];
    if (!entityId || !hass?.states?.[entityId]) continue;
    const raw = parseInt(String(hass.states[entityId].state), 10);
    if (!Number.isFinite(raw) || raw === 0) continue;
    const bits = FOX_BMS_FAULT_BITS[i - 1] || [];
    bits.forEach((label, bit) => {
      if (!label || (raw & (1 << bit)) === 0) return;
      active.push({ register: `BS${i}`, code: FOX_BMS_E_CODES[bit], label });
    });
  }
  return active;
}

/**
 * @param {string} alarmName
 * @param {{ hass?: Record<string, unknown>, map?: Record<string, string>, esc: (s: string) => string }} ctx
 */
export function renderFoxAlarmDetailBody(alarmName, ctx) {
  const { hass, map = {}, esc } = ctx;
  const guide = foxAlarmGuideEntry(alarmName);
  const solutions = guide.solutions
    .map((s) => `<li>${esc(s)}</li>`)
    .join("");

  let bmsHtml = "";
  if (guide.bmsRelated && hass) {
    const faults = decodeBmsFaultRegisters(hass, map);
    const bmsOnline = map.bms_online && hass.states?.[map.bms_online];
    const batStatus = map.battery_status && hass.states?.[map.battery_status];
    const rows =
      faults.length > 0
        ? faults
            .map(
              (f) =>
                `<tr><td>${esc(f.register)}</td><td>${esc(f.code)}</td><td>${esc(bmsBitDisplayName(f.label))}</td></tr>`
            )
            .join("")
        : `<tr><td colspan="3">${esc(tl("alerts.no_active_bms_fault_bits_reported"))}</td></tr>`;

    bmsHtml = `<section class="fox-alarm-detail-section">
<h3 class="fox-alarm-detail-subtitle">${tl("alerts.bms_status")}</h3>
<dl class="fox-alarm-detail-meta">
${bmsOnline ? `<div><dt>${tl("settings.bms_online")}</dt><dd>${esc(bmsOnline.state === "on" ? tl("alerts.online") : tl("alerts.offline"))}</dd></div>` : ""}
${batStatus ? `<div><dt>${tl("alerts.battery_status")}</dt><dd>${esc(batStatus.state)}</dd></div>` : ""}
</dl>
<h4 class="fox-alarm-detail-bits-title">${tl("alerts.decoded_bms_faults_bs1_bs6")}</h4>
<div class="fox-alarm-detail-table-wrap"><table class="fox-alarm-detail-table"><thead><tr><th>${tl("alerts.register")}</th><th>${tl("alerts.code")}</th><th>${tl("alerts.fault")}</th></tr></thead><tbody>${rows}</tbody></table></div>
<p class="fox-alarm-detail-note">${esc(tl("alerts.example_from_manual_bs1_e03_ext"))}</p>
</section>`;
  }

  return `<div class="fox-alarm-detail-body">
<p class="fox-alarm-detail-manual"><span class="fox-alarm-detail-label">${tl("alerts.reported_as")}</span> ${esc(guide.manualName)}</p>
<p class="fox-alarm-detail-desc">${esc(guide.description)}</p>
<h3 class="fox-alarm-detail-subtitle">${tl("alerts.suggested_actions")}</h3>
<ul class="fox-alarm-detail-solutions">${solutions}</ul>
${bmsHtml}
<p class="fox-alarm-detail-source">${tl("alerts.guidance_based_on_the_foxess_evo")}</p>
</div>`;
}

/** @param {string} alarmName */
export function renderFoxAlarmDetailModal(alarmName, ctx) {
  const { esc } = ctx;
  return `<div class="fox-help-modal-backdrop" data-fox-alarm-detail-modal="1" data-action="device-alarm-detail-backdrop">
<div class="fox-help-modal fox-alarm-detail-modal" data-action="device-alarm-detail-dialog" role="dialog" aria-modal="true" aria-labelledby="fox-alarm-detail-title">
<button type="button" class="fox-help-modal-close" data-action="device-alarm-detail-close" aria-label="${tl("energy.close")}">×</button>
<h2 id="fox-alarm-detail-title" class="fox-help-modal-title">${esc(alarmDisplayName(alarmName))}</h2>
${renderFoxAlarmDetailBody(alarmName, ctx)}
<div class="fox-help-modal-footer">
<button type="button" class="fox-help-modal-ok" data-action="device-alarm-detail-close">${tl("energy.close")}</button>
</div>
</div>
</div>`;
}
