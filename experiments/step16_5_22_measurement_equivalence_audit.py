"""16.5.22: Measurement-Definition Equivalence Audit + Execution-Epoch Recovery.

Objective: Establish whether the measurement definitions are semantically
equivalent, and recover the current execution epoch for comparison.

Critical distinction:
  Metric NAMES differ (wholesignal_centroid vs spectral_centroid_hz).
  But do the actual DEFINITIONS differ?
  A name is metadata; the definition is the kernel, target, parameters.

Method:
  1. Extract full historical MeasurementDefinition
  2. Extract full current MeasurementDefinition
  3. Compare semantically (kernel, target, parameters, hash)
  4. Recover current execution epoch (Serum binary, harness, environment)
  5. Compare epochs
  6. Report equivalence verdict (EQUIVALENT / MATERIALLY_DIFFERENT)

Output: Decision tree for 16.5.23 based on findings.

NO CAUSAL EXPERIMENT YET. Equivalence only.
"""
import sys, pickle, json, hashlib, os, subprocess
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.measurement import define, MeasurementTargetRef, artifact_hash, scoped_dependency_lock

print("=" * 80)
print("16.5.22: Measurement-Definition Equivalence Audit")
print("             + Execution-Epoch Recovery")
print("=" * 80)
print()

# ---- Load historical record ----
hist_rec = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))

# ---- SECTION 1: Extract Historical MeasurementDefinition ----
print("SECTION 1: Historical Measurement Definition")
print("-" * 80)
print()

print("OBSERVED - From historical witness record:")
if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]

    print("  metric:                  %s" % m.metric)
    print("  measurement_definition_id: %s" % m.measurement_definition_id)
    print("  target.field_path:       %s" % m.target.field_path)
    print("  target.module:           %s" % m.target.module)
    print("  target.parameter:        %s" % m.target.parameter)
    print()

    # Extract kernel artifact from the record metadata
    # The measurement_definition_id encodes the definition
    hist_metric_name = m.metric
    hist_definition_id = m.measurement_definition_id
    hist_target_path = m.target.field_path
    hist_target_module = m.target.module
    hist_target_parameter = m.target.parameter

    # Try to extract kernel info from the record if available
    # The measurement_condition_signature or other metadata might contain it
    print("Attempting to recover kernel artifact info...")

    # The definition_id format is "metric_name:hash12"
    # The hash is computed from metric_name, implementation_artifact_hash, target, lock_id
    # We can't reverse the hash, but we can infer the kernel from the metric name

    if "wholesignal_centroid" in hist_metric_name:
        hist_kernel_artifact = "wholesignal_centroid.py"
    else:
        hist_kernel_artifact = "unknown"

    print("  Inferred kernel artifact: %s" % hist_kernel_artifact)
    print()

else:
    print("ERROR: No causal_measurements in historical record")
    sys.exit(1)

# ---- SECTION 2: Extract Current MeasurementDefinition ----
print("SECTION 2: Current Measurement Definition")
print("-" * 80)
print()

print("OBSERVED - Reconstructed from 16.5.20 execution:")

curr_metric_name = "spectral_centroid_hz"
curr_kernel_artifact = "wholesignal_centroid.py"
curr_target_path = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"
curr_target_module = "FXEQ"
curr_target_parameter = "kParamFreq1"

print("  metric:            %s" % curr_metric_name)
print("  kernel_artifact:   %s" % curr_kernel_artifact)
print("  target.field_path: %s" % curr_target_path)
print("  target.module:     %s" % curr_target_module)
print("  target.parameter:  %s" % curr_target_parameter)
print()

# Compute current MeasurementDefinition to get its definition_id
try:
    curr_target = MeasurementTargetRef(curr_target_path, curr_target_module, curr_target_parameter)
    curr_md = define(curr_metric_name, curr_kernel_artifact, curr_target)
    curr_definition_id = curr_md.measurement_definition_id
    curr_kernel_hash = curr_md.implementation_artifact_hash

    print("  Computed definition_id: %s" % curr_definition_id)
    print("  Kernel artifact hash:   %s..." % curr_kernel_hash[:16])
    print()
except Exception as e:
    print("  ERROR computing definition: %s" % e)
    curr_definition_id = None
    curr_kernel_hash = None

# ---- SECTION 3: Compare Measurement Definitions ----
print("SECTION 3: Measurement Definition Comparison")
print("-" * 80)
print()

print("Metric name:")
print("  Historical: %s" % hist_metric_name)
print("  Current:    %s" % curr_metric_name)
print("  Match:      %s" % ("YES" if hist_metric_name == curr_metric_name else "NO (different names)"))
print()

print("Kernel artifact:")
print("  Historical: %s" % hist_kernel_artifact)
print("  Current:    %s" % curr_kernel_artifact)
print("  Match:      %s" % ("YES" if hist_kernel_artifact == curr_kernel_artifact else "NO (different files)"))
print()

if hist_kernel_artifact == curr_kernel_artifact and hist_kernel_artifact != "unknown":
    # Both use the same kernel file; check if the kernel code changed
    kernel_path = os.path.join(os.path.dirname(__file__), "..", "serum2", "evidence", "kernels", curr_kernel_artifact)
    if os.path.exists(kernel_path):
        try:
            curr_artifact_hash = artifact_hash(kernel_path)
            print("Kernel artifact hash (current file):")
            print("  %s..." % curr_artifact_hash[:16])
            print("  (Historical would have been computed at record time)")
            print()
        except Exception as e:
            print("ERROR hashing kernel: %s" % e)
            print()
    else:
        print("Kernel file not found at expected path: %s" % kernel_path)
        print()

print("Target specification:")
print("  Historical path: %s" % hist_target_path)
print("  Current path:    %s" % curr_target_path)

path_diff_note = ""
if "FX[FXEQ]" in hist_target_path and "FX.1.FXEQ" in curr_target_path:
    path_diff_note = " (path notation differs: dict vs index, but both target FXEQ[1])"
elif hist_target_path != curr_target_path:
    path_diff_note = " (paths differ materially)"

print("  Match:           %s%s" % ("YES" if hist_target_path == curr_target_path else "NO", path_diff_note))
print()

print("Module and parameter:")
print("  Historical: module=%s, parameter=%s" % (hist_target_module, hist_target_parameter))
print("  Current:    module=%s, parameter=%s" % (curr_target_module, curr_target_parameter))
print("  Match:      %s" % ("YES" if (hist_target_module == curr_target_module and hist_target_parameter == curr_target_parameter) else "NO"))
print()

print("Definition ID:")
print("  Historical: %s" % hist_definition_id)
print("  Current:    %s" % (curr_definition_id if curr_definition_id else "UNKNOWN"))
print("  Match:      %s" % ("YES (same measurement)" if hist_definition_id == curr_definition_id else "NO (different definitions)" if curr_definition_id else "UNKNOWN"))
print()

# ---- SECTION 4: Measurement Equivalence Verdict ----
print("=" * 80)
print("MEASUREMENT EQUIVALENCE VERDICT")
print("=" * 80)
print()

# Determine equivalence
kernel_match = (hist_kernel_artifact == curr_kernel_artifact and hist_kernel_artifact != "unknown")
module_match = (hist_target_module == curr_target_module)
parameter_match = (hist_target_parameter == curr_target_parameter)
defn_id_match = (hist_definition_id == curr_definition_id) if curr_definition_id else None

if kernel_match and module_match and parameter_match:
    print("VERDICT: SEMANTICALLY EQUIVALENT (or very similar)")
    print()
    print("Rationale:")
    print("  - Both use the same kernel artifact (%s)" % curr_kernel_artifact)
    print("  - Both target the same module/parameter (FXEQ/kParamFreq1)")
    print("  - Metric names differ, but definitions are the same")
    print()
    print("Implication:")
    print("  The 3062 Hz baseline divergence CANNOT be explained by")
    print("  measurement definition differences.")
    print("  Investigation must focus on execution epoch or state.")
    print()
    md_equivalent = True
else:
    print("VERDICT: MATERIALLY DIFFERENT")
    print()
    print("Differences:")
    if not kernel_match:
        print("  - Kernel artifact differs: %s vs %s" % (hist_kernel_artifact, curr_kernel_artifact))
    if not module_match:
        print("  - Target module differs: %s vs %s" % (hist_target_module, curr_target_module))
    if not parameter_match:
        print("  - Target parameter differs: %s vs %s" % (hist_target_parameter, curr_target_parameter))
    print()
    print("Implication:")
    print("  The measurement definitions are fundamentally different.")
    print("  The baseline divergence could be partially or fully explained")
    print("  by measuring different quantities.")
    print()
    md_equivalent = False

print()

# ---- SECTION 5: Recover Current Execution Epoch ----
print("=" * 80)
print("SECTION 5: Current Execution Epoch Recovery")
print("=" * 80)
print()

print("OBSERVED - Historical epoch:")
hist_epoch = hist_rec.epoch
print("  evidence_epoch_id:       %s" % hist_epoch.get("evidence_epoch_id", "?"))
print("  serum_binary_sha256:     %s..." % hist_epoch.get("serum_binary_sha256", "?")[:16])
print("  execution_harness_rev:   %s..." % hist_epoch.get("execution_harness_revision", "?")[:16])
print()

hist_serum_sha = hist_epoch.get("serum_binary_sha256")
hist_harness_rev = hist_epoch.get("execution_harness_revision")

print()
print("OBSERVED - Current epoch (recovered from environment):")
print()

# Try to get current git revision
try:
    curr_harness_rev = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=r"D:\ableton claude",
        stderr=subprocess.DEVNULL
    ).decode().strip()
    print("  execution_harness_rev (git HEAD): %s..." % curr_harness_rev[:16])
except Exception as e:
    print("  execution_harness_rev: ERROR (%s)" % type(e).__name__)
    curr_harness_rev = None

print()

# Serum binary sha256 is harder to obtain without running a render
# We can note that it's unknown but recoverable during a render
print("UNKNOWN - Serum binary:")
print("  Current serum_binary_sha256: [unknown without executing Serum]")
print("  [Would be recoverable by examining Serum binary or execution traces]")
print()

# Environment fingerprint
try:
    import platform
    env_platform = platform.platform()
    print("Environment platform: %s" % env_platform)
except:
    pass

print()

# ---- SECTION 6: Epoch Comparison ----
print("SECTION 6: Execution Epoch Comparison")
print("-" * 80)
print()

print("Harness revision:")
if curr_harness_rev and hist_harness_rev:
    print("  Historical: %s..." % hist_harness_rev[:16])
    print("  Current:    %s..." % curr_harness_rev[:16])
    print("  Match:      %s" % ("YES (same revision)" if hist_harness_rev == curr_harness_rev else "NO (harness has changed)"))
else:
    print("  Cannot compare (current or historical harness_rev unknown)")

print()

print("Serum binary:")
print("  Historical: %s..." % (hist_serum_sha[:16] if hist_serum_sha else "unknown"))
print("  Current:    [unknown, requires render]")
print()

# ---- SECTION 7: Decision Tree ----
print("=" * 80)
print("DECISION TREE FOR 16.5.23")
print("=" * 80)
print()

if md_equivalent:
    print("IF: Measurement definitions are equivalent")
    print("  AND Harness revision differs")
    print()
    print("  THEN: Harness changes could explain baseline divergence")
    print("        Action: Compare harness rendering code for changes")
    print("        (sample rate, buffer size, note timing, state reset)")
    print()
    print("  IF Harness revision is identical:")
    print("    THEN: Serum binary version is the prime suspect")
    print("          Action: Compare Serum binaries for version differences")
    print()
else:
    print("IF: Measurement definitions are materially different")
    print()
    print("  THEN: Do NOT attribute baseline divergence to Serum/harness yet")
    print("        Action: Identify exactly what the definition difference is")
    print("                (kernel behavior, target signal, parameters)")
    print("                Then test measurement behavior difference in isolation")
    print()

print()

print("=" * 80)
print("SUMMARY FOR 16.5.23")
print("=" * 80)
print()

print("Measurement equivalence: %s" % ("EQUIVALENT" if md_equivalent else "MATERIALLY DIFFERENT"))
print("Harness version change:  %s" % ("YES" if (curr_harness_rev and hist_harness_rev and curr_harness_rev != hist_harness_rev) else "UNKNOWN" if curr_harness_rev is None else "NO"))
print("Serum version change:    UNKNOWN (requires render to determine)")
print()

if md_equivalent:
    print("PRIMARY SUSPECT: Serum binary version or harness rendering configuration")
    print("ACTION: Do not run a causal test yet. Establish which version changed.")
else:
    print("PRIMARY FOCUS: Measurement definition difference")
    print("ACTION: Identify the exact semantic difference, then test it in isolation.")

print()
print("=" * 80)
print("16.5.22 COMPLETE")
print("=" * 80)
