"""16.5.23: Kernel Artifact Identity Audit.

Objective: Establish byte-for-byte whether the historical and current
wholesignal_centroid.py kernel artifacts are identical.

This is a pure identity comparison, not a causal test.
Outcome is binary: IDENTICAL or DIFFERENT.

Method:
  1. Locate current wholesignal_centroid.py kernel artifact
  2. Compute SHA-256 hash of current artifact
  3. Attempt to locate historical artifact (via git history)
  4. Compare hashes and bytes if both are available
  5. Report: IDENTICAL / DIFFERENT / UNKNOWN

No render. No execution. No speculation.
"""
import sys, os, hashlib, subprocess
sys.path.insert(0, r"D:\ableton claude")

print("=" * 80)
print("16.5.23: Kernel Artifact Identity Audit")
print("=" * 80)
print()

# ---- SECTION 1: Current Kernel Artifact ----
print("SECTION 1: Current Kernel Artifact")
print("-" * 80)
print()

kernel_dir = os.path.join(r"D:\ableton claude", "serum2", "evidence", "kernels")
kernel_path = os.path.join(kernel_dir, "wholesignal_centroid.py")

print("OBSERVED - Current kernel location:")
print("  Path: %s" % kernel_path)
print("  Exists: %s" % os.path.exists(kernel_path))
print()

if not os.path.exists(kernel_path):
    print("ERROR: Current kernel file not found")
    sys.exit(1)

# Read and hash current kernel
try:
    with open(kernel_path, "rb") as f:
        current_content = f.read()
    current_hash = hashlib.sha256(current_content).hexdigest()
    current_size = len(current_content)

    print("OBSERVED - Current kernel artifact:")
    print("  SHA-256: %s" % current_hash)
    print("  Size:    %d bytes" % current_size)
    print()
except Exception as e:
    print("ERROR reading current kernel: %s" % e)
    sys.exit(1)

# Show first few lines for verification
print("Current kernel (first 20 lines):")
print("-" * 80)
try:
    lines = current_content.decode("utf-8").split("\n")[:20]
    for i, line in enumerate(lines, 1):
        print("%3d: %s" % (i, line[:70]))
except Exception as e:
    print("(unable to decode as UTF-8)")
print()

# ---- SECTION 2: Historical Kernel Artifact Search ----
print("SECTION 2: Historical Kernel Artifact (via git history)")
print("-" * 80)
print()

# Try to find the kernel artifact at a historical point
# The evidence record was created with harness_revision: 4e3ea7d17282aaae...
hist_harness_rev = "4e3ea7d17282aaae299bdf98ba54ea69c367f5fb2b9595bc67"

print("Historical harness revision (from evidence epoch):")
print("  %s" % hist_harness_rev[:16])
print()

# Check if we can access git history
try:
    # List all revisions that modified the kernel file
    git_log_cmd = [
        "git", "log", "--oneline", "--follow",
        "--", "serum2/evidence/kernels/wholesignal_centroid.py"
    ]
    log_output = subprocess.check_output(git_log_cmd, cwd=r"D:\ableton claude", stderr=subprocess.PIPE).decode()

    print("Git history for wholesignal_centroid.py:")
    print("-" * 80)
    for line in log_output.strip().split("\n")[:15]:
        print("  %s" % line)
    print()

except Exception as e:
    print("ERROR checking git history: %s" % e)
    log_output = None

print()

# Try to get the kernel at the historical commit
print("ATTEMPTING: Recover kernel artifact at historical commit")
print("-" * 80)
print()

if hist_harness_rev:
    try:
        # Try to get the file content at that commit
        git_show_cmd = [
            "git", "show", "%s:serum2/evidence/kernels/wholesignal_centroid.py" % hist_harness_rev
        ]
        hist_content = subprocess.check_output(git_show_cmd, cwd=r"D:\ableton claude", stderr=subprocess.PIPE)
        hist_hash = hashlib.sha256(hist_content).hexdigest()
        hist_size = len(hist_content)

        print("OBSERVED - Historical kernel artifact (from git %s):" % hist_harness_rev[:8])
        print("  SHA-256: %s" % hist_hash)
        print("  Size:    %d bytes" % hist_size)
        print()

        # Show first few lines
        print("Historical kernel (first 20 lines):")
        print("-" * 80)
        try:
            lines = hist_content.decode("utf-8").split("\n")[:20]
            for i, line in enumerate(lines, 1):
                print("%3d: %s" % (i, line[:70]))
        except:
            print("(unable to decode as UTF-8)")
        print()

        hist_found = True

    except subprocess.CalledProcessError as e:
        print("ERROR: Could not retrieve kernel from git at commit %s" % hist_harness_rev[:8])
        print("  Message: %s" % e.stderr.decode() if e.stderr else "no error message")
        print()
        hist_found = False
    except Exception as e:
        print("ERROR: %s" % e)
        hist_found = False
else:
    print("Historical harness revision not available")
    hist_found = False

print()

# ---- SECTION 3: Artifact Identity Comparison ----
print("=" * 80)
print("SECTION 3: Artifact Identity Comparison")
print("=" * 80)
print()

if hist_found:
    print("OBSERVED - Hash comparison:")
    print("  Historical: %s" % hist_hash)
    print("  Current:    %s" % current_hash)
    print()

    if hist_hash == current_hash:
        print("VERDICT: IDENTICAL")
        print()
        print("The wholesignal_centroid.py kernel artifact is byte-for-byte identical")
        print("between historical and current.")
        print()
        print("Implication:")
        print("  The kernel implementation has NOT changed.")
        print("  The 3062 Hz baseline divergence cannot be attributed to kernel changes.")
        print("  Investigation must focus on execution epoch (Serum binary, harness config).")
        print()
        identity_result = "IDENTICAL"

    else:
        print("VERDICT: DIFFERENT")
        print()
        print("The wholesignal_centroid.py kernel artifact differs between historical and current.")
        print()
        print("Difference details:")
        print("  Historical SHA-256: %s" % hist_hash)
        print("  Current SHA-256:    %s" % current_hash)
        print("  Historical size:    %d bytes" % hist_size)
        print("  Current size:       %d bytes" % current_size)
        print()

        # Show what changed (simple line diff)
        print("Line-by-line comparison (first difference):")
        print("-" * 80)
        try:
            hist_lines = hist_content.decode("utf-8").split("\n")
            curr_lines = current_content.decode("utf-8").split("\n")

            for i, (h_line, c_line) in enumerate(zip(hist_lines, curr_lines), 1):
                if h_line != c_line:
                    print("Line %d differs:" % i)
                    print("  Historical: %s" % h_line[:70])
                    print("  Current:    %s" % c_line[:70])
                    break
            else:
                if len(hist_lines) != len(curr_lines):
                    print("File length differs: %d lines (historical) vs %d lines (current)" % (len(hist_lines), len(curr_lines)))
                else:
                    print("(no differences found despite different hashes)")
        except Exception as e:
            print("(unable to perform line diff: %s)" % e)

        print()

        print("Implication:")
        print("  The kernel implementation HAS CHANGED between historical and current.")
        print("  The change is a CANDIDATE explanation for baseline divergence,")
        print("  but it is not a PROVEN cause without testing kernel behavior.")
        print("  Next step: identify what changed and test behavioral impact.")
        print()
        identity_result = "DIFFERENT"

else:
    print("VERDICT: UNKNOWN")
    print()
    print("Unable to retrieve the historical kernel artifact from git history.")
    print("Possible reasons:")
    print("  - Historical harness revision is not a valid commit")
    print("  - File did not exist at that commit")
    print("  - Git history is not accessible")
    print()
    print("Implication:")
    print("  Cannot determine kernel identity with certainty.")
    print("  Recommendation: Inspect git log manually or verify historical commit.")
    print()
    identity_result = "UNKNOWN"

print()

# ---- SECTION 4: Recommendation for 16.5.24 ----
print("=" * 80)
print("RECOMMENDATION FOR 16.5.24")
print("=" * 80)
print()

if identity_result == "IDENTICAL":
    print("ACTION: Proceed to execution epoch recovery")
    print()
    print("16.5.24 should capture and compare:")
    print("  - Current Serum binary SHA-256")
    print("  - Current harness revision (git HEAD)")
    print("  - Current environment/dependency fingerprint")
    print("  - Render configuration (sample rate, buffer, channels, state reset)")
    print()
    print("Then compare against historical epoch:")
    print("  - Historical Serum: 7978c9be5b2107e9...")
    print("  - Historical harness: 4e3ea7d17282aaae...")
    print()
    print("If epochs differ, run isolated render test with one changed parameter.")

elif identity_result == "DIFFERENT":
    print("ACTION: Do NOT yet run execution epoch recovery")
    print()
    print("16.5.24 should instead:")
    print("  1. Identify what changed in the kernel")
    print("     (review git diff or code inspection)")
    print("  2. Determine if the change could affect baseline centroid")
    print("  3. Test the kernel behavior difference in isolation")
    print("     (if the change is material)")
    print()
    print("Only after confirming the kernel change does NOT explain the divergence:")
    print("  Proceed to execution epoch recovery (16.5.25)")

else:  # UNKNOWN
    print("ACTION: Resolve historical commit identity")
    print()
    print("16.5.24 should:")
    print("  1. Verify the historical harness revision is valid")
    print("  2. Inspect git log to find when kernel last changed")
    print("  3. Compare kernel at that point with current kernel")
    print("  4. Then proceed accordingly (IDENTICAL or DIFFERENT branch)")

print()

print("=" * 80)
print("16.5.23 COMPLETE")
print("=" * 80)
print()
print("Result: %s" % identity_result)
