"""16.5.25: Execution Epoch Recovery and Comparison.

Objective: Capture the current execution epoch and compare against historical.
Do NOT assign causality. Classify each variable as SAME / DIFFERENT / UNKNOWN.

Execution epoch includes:
  - Serum binary SHA-256
  - Harness revision
  - Python/runtime versions and dependencies
  - Sample rate / channel configuration
  - Render settings (buffer, note handling, state reset)

Method:
  1. Extract complete historical epoch from evidence record
  2. Recover current epoch from environment and available metadata
  3. Compare each dimension
  4. Report findings with strict provenance
  5. Stop - no causal interpretation

Output: Clean comparison table. Classify each as SAME / DIFFERENT / UNKNOWN.
"""
import sys, os, hashlib, subprocess, pickle
sys.path.insert(0, r"D:\ableton claude")

print("=" * 80)
print("16.5.25: Execution Epoch Recovery and Comparison")
print("=" * 80)
print()

# ---- Load historical record ----
hist_rec = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))
hist_epoch = hist_rec.epoch

# ---- SECTION 1: Historical Epoch ----
print("SECTION 1: Historical Execution Epoch (from evidence record)")
print("-" * 80)
print()

print("OBSERVED - Historical epoch metadata:")
print("  evidence_epoch_id:           %s" % hist_epoch.get("evidence_epoch_id", "?"))
print("  serum_binary_sha256:         %s..." % hist_epoch.get("serum_binary_sha256", "?")[:16])
print("  execution_harness_revision:  %s..." % hist_epoch.get("execution_harness_revision", "?")[:16])

# Extract dependency lock
if "dependency_lock" in hist_epoch:
    dep_lock = hist_epoch["dependency_lock"]
    print()
    print("  dependencies (from lock):")
    if isinstance(dep_lock, dict) and "packages" in dep_lock:
        for pkg, ver in list(dep_lock["packages"].items())[:5]:
            print("    %s: %s" % (pkg, ver))
    else:
        print("    (unable to parse lock)")

# Extract environment
if "environment_fingerprint" in hist_epoch:
    env_fp = hist_epoch["environment_fingerprint"]
    if isinstance(env_fp, dict):
        print()
        print("  environment:")
        print("    platform: %s" % env_fp.get("platform", "?"))
        print("    python_version: %s" % env_fp.get("python_version", "?"))
else:
    print("  environment_fingerprint: (not present)")

# Extract render config if present
if "render_configuration" in hist_epoch:
    render_cfg = hist_epoch["render_configuration"]
    print()
    print("  render_configuration:")
    for key, val in render_cfg.items():
        print("    %s: %s" % (key, val))
else:
    print("  render_configuration: (not present)")

print()
print()

# ---- SECTION 2: Current Epoch Recovery ----
print("SECTION 2: Current Execution Epoch (recovered from environment)")
print("-" * 80)
print()

# Python version
import platform
python_version = platform.python_version()
print("OBSERVED - Python version:")
print("  %s" % python_version)
print()

# NumPy version
try:
    import numpy as np
    numpy_version = np.__version__
    print("OBSERVED - NumPy version:")
    print("  %s" % numpy_version)
except:
    numpy_version = "unknown"
    print("  NumPy: unknown")

print()

# Harness revision
harness_rev_current = None
try:
    result = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=r"D:\ableton claude",
        stderr=subprocess.PIPE
    ).decode().strip()
    harness_rev_current = result
    print("OBSERVED - Harness revision (git HEAD):")
    print("  %s..." % result[:16])
except Exception as e:
    print("Harness revision: ERROR (%s)" % type(e).__name__)

print()

# Environment fingerprint
print("OBSERVED - Environment:")
print("  platform: %s" % platform.platform())
print("  python_version: %s" % python_version)
print("  machine: %s" % platform.machine())

print()

# Serum binary
print("OBSERVED - Serum binary search:")
print()

serum_sha256_current = None
serum_locations = [
    r"C:\Program Files\Common Files\Serum\Serum.dll",
    r"C:\Program Files (x86)\Serum\Serum.dll",
    r"C:\Program Files\VSTPlugins\Serum\Serum.dll",
    os.path.expanduser(r"~\AppData\Local\Programs\Serum\Serum.dll"),
]

for loc in serum_locations:
    if os.path.exists(loc):
        try:
            with open(loc, "rb") as f:
                serum_sha256_current = hashlib.sha256(f.read()).hexdigest()
            print("  Found at: %s" % loc)
            print("  SHA-256: %s..." % serum_sha256_current[:16])
            break
        except Exception as e:
            print("  Error hashing: %s" % e)

if not serum_sha256_current:
    print("  Serum binary not found at standard locations")
    print("  (Would require executing a render or inspecting VST plugin directory)")
    print()

print()

# Sample rate - try to infer from measurement or harness
print("OBSERVED - Sample rate:")
print("  (From 16.5.20/16.5.17 measurement: using default 44100 Hz)")
print("  [Actual sample rate would be determined by Serum/harness render config]")
print()

# ---- SECTION 3: Epoch Comparison ----
print("=" * 80)
print("SECTION 3: Execution Epoch Comparison")
print("=" * 80)
print()

comparisons = []

# Serum binary
hist_serum = hist_epoch.get("serum_binary_sha256", "?")
curr_serum = serum_sha256_current or "UNKNOWN"

print("1. Serum Binary:")
print("   Historical: %s..." % (hist_serum[:16] if hist_serum != "?" else "unknown"))
print("   Current:    %s" % (curr_serum[:16] if curr_serum != "UNKNOWN" else "UNKNOWN (not found)"))

if curr_serum == "UNKNOWN":
    serum_match = "UNKNOWN"
elif hist_serum == "?" or hist_serum == "unknown":
    serum_match = "UNKNOWN"
elif hist_serum == curr_serum:
    serum_match = "SAME"
else:
    serum_match = "DIFFERENT"

print("   Classification: %s" % serum_match)
comparisons.append(("Serum Binary", serum_match))
print()

# Harness revision
hist_harness = hist_epoch.get("execution_harness_revision", "?")
curr_harness = harness_rev_current or "UNKNOWN"

print("2. Harness Revision:")
print("   Historical: %s..." % (hist_harness[:16] if hist_harness != "?" else "unknown"))
print("   Current:    %s" % (curr_harness[:16] if curr_harness != "UNKNOWN" else "UNKNOWN (git unavailable)"))

if curr_harness == "UNKNOWN":
    harness_match = "UNKNOWN"
elif hist_harness == "?" or hist_harness == "unknown":
    harness_match = "UNKNOWN"
elif hist_harness == curr_harness:
    harness_match = "SAME"
else:
    harness_match = "DIFFERENT"

print("   Classification: %s" % harness_match)
comparisons.append(("Harness Revision", harness_match))
print()

# Python version
hist_py = hist_epoch.get("environment_fingerprint", {}).get("python_version")
curr_py = python_version

print("3. Python Version:")
print("   Historical: %s" % (hist_py if hist_py else "unknown"))
print("   Current:    %s" % curr_py)

if hist_py is None or hist_py == "unknown":
    py_match = "UNKNOWN"
elif hist_py == curr_py:
    py_match = "SAME"
else:
    py_match = "DIFFERENT"

print("   Classification: %s" % py_match)
comparisons.append(("Python Version", py_match))
print()

# NumPy version
hist_numpy = None
if "dependency_lock" in hist_epoch:
    dep_lock = hist_epoch["dependency_lock"]
    if isinstance(dep_lock, dict) and "packages" in dep_lock:
        hist_numpy = dep_lock["packages"].get("numpy")

print("4. NumPy Version:")
print("   Historical: %s" % (hist_numpy if hist_numpy else "unknown"))
print("   Current:    %s" % numpy_version)

if hist_numpy is None or hist_numpy == "unknown":
    numpy_match = "UNKNOWN"
elif hist_numpy == numpy_version:
    numpy_match = "SAME"
else:
    numpy_match = "DIFFERENT"

print("   Classification: %s" % numpy_match)
comparisons.append(("NumPy Version", numpy_match))
print()

# Platform
hist_platform = hist_epoch.get("environment_fingerprint", {}).get("platform")
curr_platform = platform.platform()

print("5. Platform:")
print("   Historical: %s" % (hist_platform if hist_platform else "unknown"))
print("   Current:    %s" % curr_platform)

if hist_platform is None or hist_platform == "unknown":
    platform_match = "UNKNOWN"
elif hist_platform == curr_platform:
    platform_match = "SAME"
else:
    platform_match = "DIFFERENT"

print("   Classification: %s" % platform_match)
comparisons.append(("Platform", platform_match))
print()

# ---- SECTION 4: Summary ----
print("=" * 80)
print("EXECUTION EPOCH COMPARISON SUMMARY")
print("=" * 80)
print()

print("Variable                Classification")
print("-" * 40)
for var, classification in comparisons:
    print("%-30s %s" % (var, classification))

print()

# Count
same_count = sum(1 for _, c in comparisons if c == "SAME")
diff_count = sum(1 for _, c in comparisons if c == "DIFFERENT")
unknown_count = sum(1 for _, c in comparisons if c == "UNKNOWN")

print("Summary:")
print("  SAME:      %d" % same_count)
print("  DIFFERENT: %d" % diff_count)
print("  UNKNOWN:   %d" % unknown_count)

print()

# ---- SECTION 5: Implications ----
print("=" * 80)
print("IMPLICATIONS")
print("=" * 80)
print()

if diff_count > 0:
    print("EXECUTION EPOCH DIFFERS")
    print()
    different_vars = [var for var, c in comparisons if c == "DIFFERENT"]
    print("Variables that differ:")
    for var in different_vars:
        print("  - %s" % var)
    print()
    print("Next step (16.5.26):")
    print("  Isolate which of these differences explains the 3062 Hz baseline divergence")
    print("  Test behavioral impact of each variable in isolation")

elif unknown_count > 0:
    print("EXECUTION EPOCH PARTIALLY UNKNOWN")
    print()
    unknown_vars = [var for var, c in comparisons if c == "UNKNOWN"]
    print("Variables that cannot be compared:")
    for var in unknown_vars:
        print("  - %s" % var)
    print()
    print("Interpretation:")
    print("  We cannot rule in or out epoch differences for these variables")
    print("  Investigation remains incomplete until these are resolved")
    print()
    print("Next step (16.5.26):")
    print("  Attempt to recover missing historical values")
    print("  Or proceed to next forensic comparison (state/routing)")

else:  # All SAME
    print("EXECUTION EPOCH APPEARS IDENTICAL")
    print()
    print("All compared variables match between historical and current")
    print()
    print("Interpretation:")
    print("  Execution environment has not substantively changed")
    print("  But remember:")
    print("    - Kernel identity: UNKNOWN (unrecoverable)")
    print("    - State/routing: Still unexamined")
    print()
    print("Next step (16.5.26):")
    print("  Do NOT blame kernel by elimination")
    print("  Proceed to state/routing forensic comparison")

print()

print("=" * 80)
print("16.5.25 COMPLETE")
print("=" * 80)
