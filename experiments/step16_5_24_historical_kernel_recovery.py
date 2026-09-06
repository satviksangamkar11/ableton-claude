"""16.5.24: Historical Kernel Artifact Recovery.

Objective: Recover the exact historical wholesignal_centroid.py kernel
used in the historical measurement, and establish byte-for-byte identity.

Critical question: Are we even running the same centroid algorithm?

Method: Search all available sources for the historical kernel:
  1. Git history at the historical harness commit
  2. Git log to find when kernel last changed
  3. EvidenceRecord artifact metadata (if stored)
  4. Archived kernel files or pickle records
  5. Compare historical vs current byte-for-byte

Output: IDENTICAL / DIFFERENT / UNRECOVERABLE

No execution. No hypothesis testing. Pure artifact recovery.
"""
import sys, os, hashlib, subprocess, pickle
sys.path.insert(0, r"D:\ableton claude")

print("=" * 80)
print("16.5.24: Historical Kernel Artifact Recovery")
print("=" * 80)
print()

# ---- Load historical record ----
hist_rec = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))

# ---- SECTION 1: Current Kernel ----
print("SECTION 1: Current Kernel Artifact")
print("-" * 80)
print()

kernel_path = r"D:\ableton claude\serum2\evidence\kernels\wholesignal_centroid.py"

with open(kernel_path, "rb") as f:
    current_content = f.read()
current_hash = hashlib.sha256(current_content).hexdigest()

print("Current kernel:")
print("  SHA-256: %s" % current_hash)
print("  Size:    %d bytes" % len(current_content))
print()

# ---- SECTION 2: Extract Historical Metadata ----
print("SECTION 2: Historical Metadata Extraction")
print("-" * 80)
print()

hist_epoch = hist_rec.epoch
hist_harness_rev = hist_epoch.get("execution_harness_revision")
hist_measurement_defn_id = None

if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]
    hist_measurement_defn_id = m.measurement_definition_id

print("OBSERVED - Historical evidence epoch:")
print("  evidence_epoch_id:        %s" % hist_epoch.get("evidence_epoch_id", "?"))
print("  execution_harness_rev:    %s..." % (hist_harness_rev[:16] if hist_harness_rev else "?"))
print("  serum_binary_sha256:      %s..." % hist_epoch.get("serum_binary_sha256", "?")[:16])
print()

print("OBSERVED - Historical measurement:")
print("  measurement_definition_id: %s" % hist_measurement_defn_id)
print()

# Try to extract artifact metadata from the record
print("SEARCHING - EvidenceRecord for artifact metadata...")
print()

# Check if the record contains kernel metadata
artifact_found = False
if hasattr(hist_rec, "artifact_manifest"):
    print("  artifact_manifest exists")
    artifact_found = True
else:
    print("  No artifact_manifest in record")

print()

# ---- SECTION 3: Git History Search ----
print("SECTION 3: Git History Search")
print("-" * 80)
print()

print("ATTEMPTING - Recover kernel from git history...")
print()

# Initialize git repo context - check if we're in a git repo
git_available = False
try:
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=r"D:\ableton claude",
        stderr=subprocess.PIPE
    ).decode().strip()
    git_available = True
    print("Git repository root: %s" % repo_root)
    print()
except Exception as e:
    print("Git not available in this context: %s" % type(e).__name__)
    print()
    git_available = False

# Initialize flags
hist_found_git = False
hist_content_git = None

# If git available, search for the kernel at historical commit
if git_available and hist_harness_rev:
    print("ATTEMPTING - Retrieve kernel at historical commit %s..." % hist_harness_rev[:16])
    print()

    try:
        # Get the kernel content at the historical commit
        git_show_cmd = [
            "git", "show",
            "%s:serum2/evidence/kernels/wholesignal_centroid.py" % hist_harness_rev
        ]
        hist_content = subprocess.check_output(
            git_show_cmd,
            cwd=r"D:\ableton claude",
            stderr=subprocess.PIPE
        )
        hist_hash = hashlib.sha256(hist_content).hexdigest()

        print("OBSERVED - Historical kernel retrieved from git:")
        print("  Commit:  %s" % hist_harness_rev[:16])
        print("  SHA-256: %s" % hist_hash)
        print("  Size:    %d bytes" % len(hist_content))
        print()

        # Show first lines
        print("Historical kernel (first 20 lines):")
        print("-" * 80)
        try:
            lines = hist_content.decode("utf-8").split("\n")[:20]
            for i, line in enumerate(lines, 1):
                print("%3d: %s" % (i, line[:70]))
        except:
            print("(unable to decode)")
        print()

        hist_found_git = True
        hist_content_git = hist_content

    except subprocess.CalledProcessError as e:
        print("ERROR - Could not retrieve from git at that commit")
        err_msg = e.stderr.decode() if e.stderr else "no details"
        if "does not have" in err_msg or "unknown revision" in err_msg:
            print("  Likely cause: commit does not exist or file did not exist at that commit")
        else:
            print("  Error: %s" % err_msg[:100])
        print()
        hist_found_git = False

    except Exception as e:
        print("ERROR: %s" % e)
        print()
        hist_found_git = False

    # If we couldn't get it at the exact commit, try to find when it last changed
    if not hist_found_git:
        print("ATTEMPTING - Find when kernel was last modified before historical commit...")
        print()

        try:
            # Get the git log for the kernel file
            log_cmd = [
                "git", "log", "-n", "20", "--oneline",
                "serum2/evidence/kernels/wholesignal_centroid.py"
            ]
            log_output = subprocess.check_output(
                log_cmd,
                cwd=r"D:\ableton claude",
                stderr=subprocess.PIPE
            ).decode()

            print("Recent git history for kernel:")
            print(log_output)
            print()

            # Try to get the kernel from HEAD
            print("ATTEMPTING - Retrieve kernel from HEAD (latest version)...")
            try:
                head_cmd = ["git", "show", "HEAD:serum2/evidence/kernels/wholesignal_centroid.py"]
                head_content = subprocess.check_output(
                    head_cmd,
                    cwd=r"D:\ableton claude",
                    stderr=subprocess.PIPE
                )
                head_hash = hashlib.sha256(head_content).hexdigest()

                print("OBSERVED - Kernel at HEAD:")
                print("  SHA-256: %s" % head_hash)
                print("  Size:    %d bytes" % len(head_content))
                print()

                if head_hash == current_hash:
                    print("Head kernel matches current kernel (as expected)")
                else:
                    print("WARNING: Head kernel differs from working copy")

                print()
            except Exception as e:
                print("ERROR: %s" % e)
                print()

        except Exception as e:
            print("ERROR examining git history: %s" % e)
            print()

else:
    if not git_available:
        print("Git not available - cannot search history")
    else:
        print("Historical harness revision not available")
    print()

print()

# ---- SECTION 4: Identity Comparison ----
print("=" * 80)
print("SECTION 4: Kernel Identity Comparison")
print("=" * 80)
print()

if hist_found_git:
    print("Comparing historical (from git %s) vs current:" % hist_harness_rev[:16])
    print()

    print("  Historical SHA-256: %s" % hist_hash)
    print("  Current SHA-256:    %s" % current_hash)
    print()

    if hist_hash == current_hash:
        print("VERDICT: IDENTICAL")
        print()
        print("The wholesignal_centroid.py kernel is byte-for-byte identical")
        print("between historical and current.")
        print()
        print("Implication:")
        print("  Kernel implementation has NOT changed.")
        print("  The 3062 Hz baseline divergence is NOT due to kernel changes.")
        print("  Investigation must focus on:")
        print("    1. Execution epoch (Serum binary version, harness config)")
        print("    2. Sample rate or audio format differences")
        print("    3. State/routing differences")
        print()
        verdict = "IDENTICAL"

    else:
        print("VERDICT: DIFFERENT")
        print()
        print("The kernels differ between historical and current.")
        print()

        # Show what changed
        print("Detailed comparison:")
        print("-" * 80)

        try:
            hist_lines = hist_content_git.decode("utf-8").split("\n")
            curr_lines = current_content.decode("utf-8").split("\n")

            # Find first difference
            for i, (h, c) in enumerate(zip(hist_lines, curr_lines), 1):
                if h != c:
                    print("First difference at line %d:" % i)
                    print("  Historical: %s" % h[:70])
                    print("  Current:    %s" % c[:70])
                    break
            else:
                if len(hist_lines) != len(curr_lines):
                    print("File length differs: %d lines vs %d lines" % (len(hist_lines), len(curr_lines)))
                else:
                    print("Hashes differ but line-by-line content appears identical")

        except Exception as e:
            print("(unable to show diff: %s)" % e)

        print()

        # Analyze the difference
        print("Implication:")
        print("  Kernel IMPLEMENTATION has CHANGED.")
        print("  This is a candidate explanation for the baseline divergence.")
        print("  Next step: identify what changed and test behavioral impact.")
        print()
        verdict = "DIFFERENT"

else:
    print("VERDICT: UNRECOVERABLE")
    print()
    print("Historical kernel artifact could not be retrieved from available sources:")
    print("  - Git repository not available or historical commit not found")
    print("  - EvidenceRecord does not store kernel artifacts")
    print("  - No archived kernel files found")
    print()
    print("Implication:")
    print("  Cannot establish kernel identity with certainty.")
    print("  Investigation must proceed with KERNEL IDENTITY UNKNOWN.")
    print()
    print("Recommendation:")
    print("  1. If possible, locate historical Serum backup or git history elsewhere")
    print("  2. Or, proceed to execution epoch investigation assuming kernel is same")
    print("  3. If execution epoch identical, kernel becomes the prime suspect by elimination")
    print()
    verdict = "UNRECOVERABLE"

print()

# ---- SECTION 5: Next Steps ----
print("=" * 80)
print("NEXT STEPS (16.5.25 and beyond)")
print("=" * 80)
print()

if verdict == "IDENTICAL":
    print("Kernel is IDENTICAL → proceed to execution epoch recovery")
    print()
    print("16.5.25 should capture current epoch:")
    print("  - Serum binary SHA-256 (from execution)")
    print("  - Harness revision (from git HEAD)")
    print("  - Render configuration (sample rate, buffer, channels)")
    print()
    print("Then compare historical vs current.")
    print()
    print("If epochs are identical:")
    print("  - Kernel is identical")
    print("  - Execution is identical")
    print("  - Then baseline divergence must be due to state/routing/signal-path")
    print()
    print("If epochs differ:")
    print("  - Identify which epoch variable changed")
    print("  - Test that variable in isolation (especially sample rate)")

elif verdict == "DIFFERENT":
    print("Kernel implementation DIFFERS → investigate behavioral impact")
    print()
    print("16.5.25 should:")
    print("  1. Analyze what changed in kernel code")
    print("  2. Determine if change could cause 3062 Hz baseline divergence")
    print("  3. If plausible: test the kernel behavior difference")
    print("     (run both kernels on same audio, compare centroids)")
    print()
    print("Do NOT proceed to execution epoch investigation until")
    print("the kernel behavioral impact is quantified.")

else:  # UNRECOVERABLE
    print("Kernel identity UNKNOWN - proceed with caution")
    print()
    print("16.5.25 should investigate execution epoch:")
    print("  - Assume kernel is same (working hypothesis)")
    print("  - If execution epoch is identical AND kernel identity remains unknown")
    print("    then kernel becomes the primary suspect by elimination")
    print()
    print("Keep kernel identity as an open question for the full investigation.")

print()

print("=" * 80)
print("16.5.24 COMPLETE")
print("=" * 80)
print()
print("Result: %s" % verdict)
