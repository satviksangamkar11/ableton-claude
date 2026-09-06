#!/usr/bin/env python3
"""Wrapper script to properly execute step16_5_50_2 with correct encoding."""

import os
import sys
import subprocess

# Set environment for UTF-8 output
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Import and run the step
if __name__ == "__main__":
    # Change to repo root
    repo_root = r"D:\ableton claude"
    os.chdir(repo_root)

    # Run the audit script
    print("=" * 80)
    print("Running: 16.5.50.2 Context-Aware Sustain Compiler Admission Audit")
    print("=" * 80)
    print()

    # Direct execution with proper encoding
    script_path = "experiments/step16_5_50_2_context_aware_sustain_admission.py"

    try:
        with open(script_path, encoding='utf-8') as f:
            code = f.read()
        exec(code)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
