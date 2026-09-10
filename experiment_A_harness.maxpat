{
  "patcher": {
    "fileversion": 1,
    "appversion": "8.6.0",
    "classnamespace": "box",
    "rect": [33, 77, 1200, 800],
    "bglocked": 0,
    "openinpresentation": 0,
    "default_fontsize": 12.0,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonset": 16,
    "gridsize": 16,
    "gridsnatrack": 1,
    "title": "Experiment A Harness v0.1 — A0/A1 Recorder",
    "boxes": [
      {
        "box": {
          "id": "obj-1",
          "maxclass": "comment",
          "text": "EXPERIMENT A HARNESS v0.1 — A0/A1 Recorder\nRecords raw vst~ observations into structured JSON artifact",
          "linecount": 2,
          "numinlets": 0,
          "numoutlets": 0,
          "patching_rect": [16.0, 16.0, 600.0, 34.0],
          "fontsize": 14.0,
          "fontweight": "bold"
        }
      },
      {
        "box": {
          "id": "obj-2",
          "maxclass": "button",
          "text": "LOAD SERUM",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [16.0, 70.0, 150.0, 30.0],
          "fontsize": 12.0
        }
      },
      {
        "box": {
          "id": "obj-3",
          "maxclass": "button",
          "text": "PROBE HOST",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [180.0, 70.0, 150.0, 30.0],
          "fontsize": 12.0
        }
      },
      {
        "box": {
          "id": "obj-4",
          "maxclass": "button",
          "text": "DUMP PARAMS",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [344.0, 70.0, 150.0, 30.0],
          "fontsize": 12.0
        }
      },
      {
        "box": {
          "id": "obj-5",
          "maxclass": "button",
          "text": "EXPORT JSON",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [508.0, 70.0, 150.0, 30.0],
          "fontsize": 12.0
        }
      },
      {
        "box": {
          "id": "obj-6",
          "maxclass": "message",
          "text": "vst~ serum",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [16.0, 120.0, 200.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-7",
          "maxclass": "object",
          "maxclass": "vst~",
          "text": "vst~",
          "numinlets": 1,
          "numoutlets": 4,
          "patching_rect": [16.0, 160.0, 300.0, 200.0],
          "saved_attribute_attributes": {
            "valueof": {
              "parameter_longname": "vst~",
              "parameter_shortname": "vst~",
              "parameter_type": 3,
              "parameter_default": 0,
              "parameter_unitstyle": 0
            }
          }
        }
      },
      {
        "box": {
          "id": "obj-8",
          "maxclass": "number",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [16.0, 380.0, 80.0, 22.0],
          "triscale": 0.9
        }
      },
      {
        "box": {
          "id": "obj-9",
          "maxclass": "message",
          "text": "get -4",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [16.0, 420.0, 200.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-10",
          "maxclass": "message",
          "text": "params",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [16.0, 460.0, 200.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-11",
          "maxclass": "textedit",
          "text": "STATUS: Ready to load Serum 2.0.21\nA0/A1 Recorder\n\nParameters discovered: 0\nExport status: pending",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [350.0, 120.0, 400.0, 300.0],
          "fontsize": 11.0,
          "readonly": 1
        }
      },
      {
        "box": {
          "id": "obj-12",
          "maxclass": "js",
          "text": "experiment_A_harness.js",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [16.0, 520.0, 300.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-13",
          "maxclass": "message",
          "text": "host_viability plugin_loaded",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [16.0, 570.0, 250.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-14",
          "maxclass": "message",
          "text": "export ./owned_host_surface.json",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [16.0, 610.0, 250.0, 22.0]
        }
      },
      {
        "box": {
          "id": "obj-15",
          "maxclass": "comment",
          "text": "CONTROL FLOW:\n1. [LOAD SERUM] → vst~ loads plugin\n2. [PROBE HOST] → verify editor/audio viability\n3. [DUMP PARAMS] → enumerate all parameters via vst~ params\n4. [EXPORT JSON] → serialize owned_host_surface.json",
          "linecount": 4,
          "numinlets": 0,
          "numoutlets": 0,
          "patching_rect": [16.0, 650.0, 600.0, 70.0],
          "fontsize": 10.0
        }
      },
      {
        "box": {
          "id": "obj-16",
          "maxclass": "comment",
          "text": "Recorder Rules (FROZEN):\n• vst~ output → structured JSON normalization only\n• NO semantic interpretation (not OSC1.Volume, not SCALAR class, not meaningful/not)\n• Preserve raw host representation (0.63 stays 0.63, symbolic as-is)\n• Use UNKNOWN for untested capabilities (MIDI, snapshot, audio)\n• All parameters enumerated, no filtering",
          "linecount": 5,
          "numinlets": 0,
          "numoutlets": 0,
          "patching_rect": [350.0, 450.0, 600.0, 90.0],
          "fontsize": 9.0,
          "fontcolor": [0.6, 0.6, 0.6]
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": ["obj-2", 0],
          "target": ["obj-6", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-6", 0],
          "target": ["obj-7", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-3", 0],
          "target": ["obj-13", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-13", 0],
          "target": ["obj-12", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-4", 0],
          "target": ["obj-10", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-10", 0],
          "target": ["obj-7", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-7", 0],
          "target": ["obj-8", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-7", 3],
          "target": ["obj-12", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-5", 0],
          "target": ["obj-14", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-14", 0],
          "target": ["obj-12", 0]
        }
      }
    ],
    "dependency_count": 0
  }
}
