/**
 * EVO user manual §10.1 fault descriptions & solutions (pp. 54–57) and BMS state decode (p. 58–59).
 * @module fox-alarm-guide
 */

/** @typedef {{ manualName: string, description: string, solutions: string[], bmsRelated?: boolean }} FoxAlarmGuideEntry */

/** EVO manual alarm list — keyed by manual fault short name. */
export const FOX_EVO_MANUAL_FAULTS = {
  "Grid Lost Fault": {
    description: "Grid is lost.",
    solutions: [
      "System will reconnect if the utility is back to normal.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Grid Volt Fault": {
    description: "Grid voltage out of range.",
    solutions: [
      "System will reconnect if the utility is back to normal.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Grid Freq Fault": {
    description: "Grid frequency out of range.",
    solutions: [
      "System will reconnect if the utility is back to normal.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "10min Volt Fault": {
    description: "The grid voltage is out of range for the last 10 minutes.",
    solutions: [
      "System will reconnect if the utility is back to normal.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "SW Inv Cur Fault": {
    description: "Output current high detected by software.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "DCI Fault": {
    description: "DC component is out of limit in output current.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "HW Inv Cur Fault": {
    description: "Output current high detected by hardware.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "SW Bus Vol Fault": {
    description: "Bus voltage out of range detected by software.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Bat Volt Fault": {
    description: "Battery voltage fault.",
    solutions: [
      "Check if the battery input voltage is within the normal range.",
      "Or seek help from us.",
    ],
    bmsRelated: true,
  },
  "SW Bat Cur Fault": {
    description: "Battery current high detected by software.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
    bmsRelated: true,
  },
  "Iso Fault": {
    description: "The isolation has failed.",
    solutions: [
      "Please check if the insulation of electric wires is damaged.",
      "Wait for a while to check if back to normal.",
      "Or seek for help from us.",
    ],
  },
  "Res Cur Fault": {
    description: "The residual current is high.",
    solutions: [
      "Please check if the insulation of electric wires is damaged.",
      "Wait for a while to check if back to normal.",
      "Or seek for help from us.",
    ],
  },
  "Pv Volt Fault": {
    description: "PV voltage out of range.",
    solutions: ["Please check the output voltage of PV panels.", "Or seek for help from us."],
  },
  "SW Pv Cur Fault": {
    description: "PV input current high detected by software.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Temp Fault": {
    description: "The inverter temperature is high.",
    solutions: [
      "Please check the environment temperature.",
      "Wait for a while to check if back to normal.",
      "Or seek for help from us.",
    ],
  },
  "Ground Fault": {
    description: "The ground connection has failed.",
    solutions: [
      "Check the voltage of neutral and PE.",
      "Check AC wiring.",
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Over Load Fault": {
    description: "Overload in on-grid mode.",
    solutions: ["Please check if the load power exceeds the limit.", "Or seek for help from us."],
  },
  "Eps Over Load": {
    description: "Overload in off-grid mode.",
    solutions: ["Please check if the EPS load power exceeds the limit.", "Or seek for help from us."],
  },
  "Bat Power Low": {
    description: "The battery power is low.",
    solutions: ["Wait for the battery to be recharged.", "Or seek for help from us."],
    bmsRelated: true,
  },
  "HW Bus Vol Fault": {
    description: "Bus voltage out of range detected by hardware.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "HW Pv Cur Fault": {
    description: "PV input current high detected by hardware.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "HW Bat Cur Fault": {
    description: "Battery current high detected by hardware.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
    bmsRelated: true,
  },
  "SCI Fault": {
    description: "The communication between master and manager has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "MDSP SPI Fault": {
    description: "The communication between master and slave has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "MDSP Smpl Fault": {
    description: "The master sample detection circuit has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Res Cur HW Fault": {
    description: "Residual current detection device has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Inv EEPROM Fault": {
    description: "The inverter EEPROM is faulty.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "PvCon Dir Fault": {
    description: "The PV connection is reversed.",
    solutions: [
      "Check if the positive pole and negative pole of PV are correctly connected.",
      "Or seek help from us.",
    ],
  },
  "Bat Relay Open": {
    description: "The battery relay keeps open.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
    bmsRelated: true,
  },
  "Bat Relay Short Circuit": {
    description: "The battery relay keeps closed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
    bmsRelated: true,
  },
  "Bat Buck Fault": {
    description: "The battery buck circuit MOSFET has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
    bmsRelated: true,
  },
  "Bat Boost Fault": {
    description: "The battery boost circuit MOSFET has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
    bmsRelated: true,
  },
  "Eps Relay Fault": {
    description: "The EPS relay has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "BatCon Dir Fault": {
    description: "The battery connection is reversed.",
    solutions: [
      "Check if the positive pole and negative pole of battery are correctly connected.",
      "Or seek help from us.",
    ],
    bmsRelated: true,
  },
  "Main Relay Open": {
    description: "The grid relay keeps open.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "S1 Close Fault": {
    description: "The grid relay S1 keeps closed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "S2 Close Fault": {
    description: "The grid relay S2 keeps closed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "M1 Close Fault": {
    description: "The grid relay M1 keeps closed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "M2 Close Fault": {
    description: "The grid relay M2 keeps closed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "GridV Cons Fault": {
    description: "Grid voltage sample values between master and slave are not consistent.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "GridF Cons Fault": {
    description: "Grid frequency sample values between master and slave are not consistent.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Dci Cons Fault": {
    description: "DCI sample values between master and slave are not consistent.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Rc Cons Fault": {
    description: "Residual current sample values between master and slave are not consistent.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "RDSP SPI Fault": {
    description: "The communication between master and slave has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "RDSP Smpl Fault": {
    description: "The slave sample detection circuit has failed.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "ARM EEPROM Fault": {
    description: "The manager EEPROM is faulty.",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "Meter Lost Fault": {
    description: "Communication between the meter and inverter is interrupted.",
    solutions: [
      "Check if the communication cable between meter and inverter is correctly and well connected.",
    ],
  },
  "DC arc fault": {
    description: "DC arc fault detected (requires arc-fault detection hardware).",
    solutions: [
      "Disconnect PV, grid and battery, then reconnect.",
      "Inspect PV wiring and connectors for damage or loose contacts.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  Islanding: {
    description: "Islanding condition detected.",
    solutions: [
      "System will reconnect if the utility is back to normal.",
      "Or seek help from us, if not go back to normal state.",
    ],
  },
  "External fan fault": {
    description: "External cooling fan fault.",
    solutions: [
      "Check that the inverter ventilation path is clear.",
      "Wait for a while to check if back to normal.",
      "Or seek for help from us.",
    ],
  },
  "BMS lost": {
    description: "Communication between the inverter and BMS is lost.",
    solutions: [
      "Check BMS communication cables and battery connections.",
      "Review active BMS fault states below (BS1–BS6).",
      "Or seek help from us, if not go back to normal state.",
    ],
    bmsRelated: true,
  },
};

/** Modbus / Fox app alarm label → EVO manual fault key. */
export const FOX_ALARM_TO_MANUAL = {
  "PV Over-voltage": "Pv Volt Fault",
  "DC arc fault": "DC arc fault",
  "String reverse connection": "PvCon Dir Fault",
  "Grid power outage": "Grid Lost Fault",
  "Abnormal grid voltage": "Grid Volt Fault",
  "Abnormal grid frequency": "Grid Freq Fault",
  "Output overcurrent": "SW Inv Cur Fault",
  "Output DC component too large": "DCI Fault",
  "Residual current": "Res Cur Fault",
  "Grounding fault": "Ground Fault",
  "Low insulation resistance": "Iso Fault",
  "Inverter overtemperature": "Temp Fault",
  "Energy storage equipment abnormal": "Bat Volt Fault",
  Islanding: "Islanding",
  "Off-grid output overload": "Eps Over Load",
  "External fan fault": "External fan fault",
  "Energy storage reverse connection": "BatCon Dir Fault",
  "Meter lost": "Meter Lost Fault",
  "BMS lost": "BMS lost",
  "Grid Lost Fault": "Grid Lost Fault",
  "Grid Voltage Fault": "Grid Volt Fault",
  "Grid Frequency Fault": "Grid Freq Fault",
  "Output Over-current Fault": "SW Inv Cur Fault",
  "Output DC Over-current Fault": "DCI Fault",
  "Residual Current Consistency Fault": "Res Cur Fault",
  "Ground Connection Fault": "Ground Fault",
  "Low Insulation Resistante Fault": "Iso Fault",
  "Inverter Over-temperature Fault": "Temp Fault",
  "Energy Storage Equipment Abnormal Fault": "Bat Volt Fault",
  "Isolated Island Fault": "Islanding",
  "Off-grid Output Overload Fault": "Eps Over Load",
  "External Fan Fault": "External fan fault",
  "Energy Storage Reverse Connection Fault": "BatCon Dir Fault",
  "Meter Lost Fault": "Meter Lost Fault",
  "BMS Lost Fault": "BMS lost",
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
  return {
    manualName: alarmName,
    description: "See EVO user manual §10.1 Alarm List for troubleshooting guidance.",
    solutions: [
      "Record the alarm message and time.",
      "Attempt the solutions in the user manual for similar faults.",
      "Contact FoxESS support if the condition persists.",
    ],
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
                `<tr><td>${esc(f.register)}</td><td>${esc(f.code)}</td><td>${esc(f.label)}</td></tr>`
            )
            .join("")
        : `<tr><td colspan="3">${esc("No active BMS fault bits reported on registers 37626–37631.")}</td></tr>`;

    bmsHtml = `<section class="fox-alarm-detail-section">
<h3 class="fox-alarm-detail-subtitle">BMS status</h3>
<dl class="fox-alarm-detail-meta">
${bmsOnline ? `<div><dt>BMS online</dt><dd>${esc(bmsOnline.state === "on" ? "Online" : "Offline")}</dd></div>` : ""}
${batStatus ? `<div><dt>Battery status</dt><dd>${esc(batStatus.state)}</dd></div>` : ""}
</dl>
<h4 class="fox-alarm-detail-bits-title">Decoded BMS faults (BS1–BS6)</h4>
<div class="fox-alarm-detail-table-wrap"><table class="fox-alarm-detail-table"><thead><tr><th>Register</th><th>Code</th><th>Fault</th></tr></thead><tbody>${rows}</tbody></table></div>
<p class="fox-alarm-detail-note">${esc("Example from manual: BS1 E03 = EXT COM + INT COM (bits b0 and b1).")}</p>
</section>`;
  }

  return `<div class="fox-alarm-detail-body">
<p class="fox-alarm-detail-manual"><span class="fox-alarm-detail-label">Manual reference</span> ${esc(guide.manualName)}</p>
<p class="fox-alarm-detail-desc">${esc(guide.description)}</p>
<h3 class="fox-alarm-detail-subtitle">Suggested actions</h3>
<ul class="fox-alarm-detail-solutions">${solutions}</ul>
${bmsHtml}
<p class="fox-alarm-detail-source">Source: EN-EVO User Manual §10.1–10.2</p>
</div>`;
}

/** @param {string} alarmName */
export function renderFoxAlarmDetailModal(alarmName, ctx) {
  const { esc } = ctx;
  return `<div class="fox-help-modal-backdrop" data-fox-alarm-detail-modal="1" data-action="device-alarm-detail-backdrop">
<div class="fox-help-modal fox-alarm-detail-modal" data-action="device-alarm-detail-dialog" role="dialog" aria-modal="true" aria-labelledby="fox-alarm-detail-title">
<button type="button" class="fox-help-modal-close" data-action="device-alarm-detail-close" aria-label="Close">×</button>
<h2 id="fox-alarm-detail-title" class="fox-help-modal-title">${esc(alarmName)}</h2>
${renderFoxAlarmDetailBody(alarmName, ctx)}
<div class="fox-help-modal-footer">
<button type="button" class="fox-help-modal-ok" data-action="device-alarm-detail-close">Close</button>
</div>
</div>
</div>`;
}
