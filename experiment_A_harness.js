// Experiment A Harness v0.1 — A0/A1 Recorder
// Records raw vst~ observations into structured JSON artifact
// NO semantic interpretation. Normalization only.

const MAX = require("max/api");

// Global state
let harness = {
  experiment: "16_5_A",
  run_id: null,
  timestamp: null,
  host: {
    application: "Ableton Live",
    container: "Max for Live",
    version: "unknown"
  },
  plugin: {
    name: null,
    version: null,
    format: "VST3",
    identifier: null
  },
  viability: {
    load: "UNKNOWN",
    editor_open: "UNKNOWN",
    audio_path: "UNKNOWN",
    midi: "UNKNOWN",
    snapshot: "UNKNOWN"
  },
  parameters: {
    count: null,
    list: []
  },
  status: "INITIALIZING",
  artifacts: []
};

// Generate run ID and timestamp
function init() {
  const now = new Date();
  harness.run_id = `A0-A1-${now.toISOString().replace(/[:.]/g, '-')}`;
  harness.timestamp = now.toISOString();
  MAX.post(`Experiment A Harness v0.1 initialized: ${harness.run_id}`);
}

// Record host viability
function record_host_viability(event) {
  // Receives: "plugin_loaded" | "editor_open" | "audio_path" | "midi_ok" | "snapshot_ok"
  MAX.post(`Recording host viability: ${event}`);

  switch(event) {
    case "plugin_loaded":
      harness.viability.load = "PASS";
      break;
    case "editor_open":
      harness.viability.editor_open = "PASS";
      break;
    case "audio_path":
      harness.viability.audio_path = "PASS";
      break;
    case "midi_ok":
      harness.viability.midi = "PASS";
      break;
    case "snapshot_ok":
      harness.viability.snapshot = "PASS";
      break;
    default:
      MAX.post(`Unknown viability event: ${event}`);
  }
}

// Record parameter
function record_parameter(index, name, normalized, symbolic) {
  // NO semantic interpretation
  // Just normalize vst~ output to stable schema

  const param = {
    index: parseInt(index),
    name: String(name),
    normalized: parseFloat(normalized),
    symbolic: String(symbolic),
    query_timestamp: new Date().toISOString()
  };

  harness.parameters.list.push(param);
}

// Set parameter count
function set_parameter_count(count) {
  harness.parameters.count = parseInt(count);
  MAX.post(`Parameter count set: ${harness.parameters.count}`);
}

// Set plugin identity
function set_plugin_identity(name, version, identifier) {
  harness.plugin.name = String(name);
  harness.plugin.version = String(version);
  harness.plugin.identifier = String(identifier);
  MAX.post(`Plugin identity: ${harness.plugin.name} v${harness.plugin.version}`);
}

// Export to JSON artifact
function export_json(output_path) {
  if (!output_path) {
    output_path = "./owned_host_surface.json";
  }

  try {
    harness.status = "COMPLETE";
    harness.artifacts = [output_path];

    const json_string = JSON.stringify(harness, null, 2);
    const file = new Max.File(output_path, "write", "TEXT");

    if (file.isopen) {
      file.writestring(json_string);
      file.close();
      MAX.post(`✓ Exported: ${output_path}`);
      MAX.outlet(`exported ${output_path}`);
    } else {
      MAX.post(`✗ Failed to open file: ${output_path}`);
    }
  } catch(e) {
    MAX.post(`✗ Export error: ${e.message}`);
  }
}

// Get current state (for debugging)
function get_state() {
  MAX.outlet(JSON.stringify(harness, null, 2));
}

// Interface to Max
MAX.addHandler("host_viability", record_host_viability);
MAX.addHandler("record_param", record_parameter);
MAX.addHandler("param_count", set_parameter_count);
MAX.addHandler("plugin_identity", set_plugin_identity);
MAX.addHandler("export", export_json);
MAX.addHandler("state", get_state);

// Initialize on load
init();
