"""Semantic Extraction Layer for YouTube Serum 2 Guide

Process raw 6,102 transcript segments into coherent semantic KnowledgeItems.
Preserve full provenance. Identify meaningful concepts, properties, procedures.
Do NOT infer Serum parameter mappings or causal claims yet.
"""

import json
import re
from typing import List, Dict, Optional
from collections import defaultdict
import hashlib

print("=" * 70)
print("SEMANTIC EXTRACTION: SERUM 2 GUIDE TRANSCRIPT")
print("=" * 70)
print()

# =========================================================================
# STEP 1: Load ingested transcript
# =========================================================================

print("-" * 70)
print("STEP 1: LOAD INGESTED TRANSCRIPT")
print("-" * 70)
print()

artifact_path = "serum2/knowledge/yt_f507169bd7cb_source_ingestion.json"

print("Loading: {}".format(artifact_path))

with open(artifact_path, 'r', encoding='utf-8') as f:
    artifact = json.load(f)

segments = artifact['transcript_segments']
source_record = artifact['source']

print("[OK] Loaded {} segments".format(len(segments)))
print()

# =========================================================================
# STEP 2: Define semantic extraction patterns
# =========================================================================

print("-" * 70)
print("STEP 2: DEFINE SEMANTIC EXTRACTION PATTERNS")
print("-" * 70)
print()

# Patterns for identifying semantic units
SEMANTIC_PATTERNS = {
    'PROCEDURE': [
        r"(?:to |how to |steps? to |process of )([\w\s]+)",
        r"(?:first|then|next|after|before|once you)\s+(?:you\s+)?(\w+)",
        r"(?:click|drag|double[\s-]?click|hold|press|select|open|load|save|export)",
    ],
    'PROPERTY': [
        r"(\w+)\s+(?:is|has|controls|affects|determines|sets?|adjusts?)\s+(?:the\s+)?(\w+)",
        r"(?:the\s+)?(\w+)\s+(?:range|value|default|maximum|minimum)",
    ],
    'RELATIONSHIP': [
        r"(\w+)\s+(?:connects?|links?|routes?|sends? to|modulates?|controls?)\s+(?:the\s+)?(\w+)",
        r"(?:when|if|depends on|based on)\s+(\w+)",
    ],
    'CONCEPT': [
        r"(?:this is|that is|it's|oscillator|filter|envelope|LFO|modulation|routing|synthesis)",
        r"(?:Serum|parameter|control|setting|feature|functionality)",
    ],
    'OPERATION': [
        r"(?:increase|decrease|boost|cut|expand|compress|modify|change|adjust|turn)",
        r"(?:enable|disable|activate|deactivate|turn on|turn off)",
    ],
    'WARNING': [
        r"(?:warning|caution|be careful|don't|avoid|never|don't forget|important)",
    ],
    'EXAMPLE': [
        r"(?:for example|like|such as|instance|let's say|imagine|suppose)",
    ],
}

print("Semantic patterns defined for:")
for kind in SEMANTIC_PATTERNS.keys():
    print("  - {}".format(kind))

print()

# =========================================================================
# STEP 3: Group segments into coherent units
# =========================================================================

print("-" * 70)
print("STEP 3: GROUP SEGMENTS INTO COHERENT UNITS")
print("-" * 70)
print()

# Strategy: Group segments based on semantic boundaries
# A new semantic unit begins when:
# - A new speaker/idea is introduced
# - A significant time gap occurs
# - Segment count indicates completion of thought

def should_start_new_unit(prev_seg, curr_seg, next_seg) -> bool:
    """Determine if current segment starts a new semantic unit."""

    # Large time gap = new topic
    time_gap = curr_seg['start_time_sec'] - prev_seg['end_time_sec']
    if time_gap > 2.0:  # >2 second gap
        return True

    # Segment text analysis
    text = curr_seg['text'].lower()

    # Topic starters
    if any(text.startswith(phrase) for phrase in [
        "hello", "hi", "welcome", "so", "now", "next", "finally",
        "in this section", "let's talk about", "we're going to"
    ]):
        return True

    # New capitalized concept (likely title)
    if curr_seg['text'][0].isupper() and len(curr_seg['text']) > 10:
        if not (prev_seg['text'][-1] in '.!?' or curr_seg['text'][0].islower()):
            return False

    return False

# Group segments into units
semantic_units = []
current_unit = [segments[0]]

for i in range(1, len(segments)):
    prev_seg = segments[i-1]
    curr_seg = segments[i]
    next_seg = segments[i+1] if i+1 < len(segments) else None

    if should_start_new_unit(prev_seg, curr_seg, next_seg):
        semantic_units.append(current_unit)
        current_unit = [curr_seg]
    else:
        current_unit.append(curr_seg)

semantic_units.append(current_unit)

print("[OK] Grouped {} segments into {} semantic units".format(
    len(segments), len(semantic_units)))
print("  Average unit size: {:.1f} segments".format(len(segments) / len(semantic_units)))
print()

# =========================================================================
# STEP 4: Extract KnowledgeItems from semantic units
# =========================================================================

print("-" * 70)
print("STEP 4: EXTRACT KNOWLEDGEITEMS FROM SEMANTIC UNITS")
print("-" * 70)
print()

extracted_items = []
item_counter = 0

for unit_idx, unit in enumerate(semantic_units):
    if unit_idx % 500 == 0:
        print("  Processing unit {}/{}...".format(unit_idx, len(semantic_units)))

    # Combine all text in unit
    combined_text = " ".join([seg['text'] for seg in unit])

    # Skip very short segments (likely filler)
    if len(combined_text) < 10:
        continue

    # Determine kind based on patterns
    kind = "SOURCE_ONLY"
    confidence = 0.0

    for test_kind, patterns in SEMANTIC_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                kind = test_kind
                confidence = 0.7  # Base confidence
                break
        if kind != "SOURCE_ONLY":
            break

    # Create extracted KnowledgeItem
    ki = {
        "knowledge_item_id": "ki_ext_{:06d}".format(item_counter),
        "source_id": source_record['source_id'],
        "source_segment_ids": [seg['segment_id'] for seg in unit],
        "segment_count": len(unit),
        "start_time_sec": unit[0]['start_time_sec'],
        "end_time_sec": unit[-1]['end_time_sec'],
        "duration_sec": unit[-1]['end_time_sec'] - unit[0]['start_time_sec'],
        "raw_source_text": combined_text,
        "kind": kind,
        "extracted_statement": combined_text[:200] + ("..." if len(combined_text) > 200 else ""),
        "extraction_status": "EXTRACTED" if kind != "SOURCE_ONLY" else "SOURCE_ONLY",
        "confidence": confidence,
    }

    extracted_items.append(ki)
    item_counter += 1

print("[OK] Extracted {} KnowledgeItems from {} semantic units".format(
    len(extracted_items), len(semantic_units)))
print()

# =========================================================================
# STEP 5: Coverage statistics
# =========================================================================

print("-" * 70)
print("STEP 5: COVERAGE STATISTICS")
print("-" * 70)
print()

# Count segments covered
covered_segment_ids = set()
for ki in extracted_items:
    covered_segment_ids.update(ki['source_segment_ids'])

coverage_pct = 100.0 * len(covered_segment_ids) / len(segments)

print("Total transcript segments: {}".format(len(segments)))
print("Extracted KnowledgeItems: {}".format(len(extracted_items)))
print("Segments covered: {} ({:.1f}%)".format(len(covered_segment_ids), coverage_pct))
print("Segments not covered: {} ({:.1f}%)".format(
    len(segments) - len(covered_segment_ids),
    100.0 - coverage_pct
))
print()

# Items by kind
kind_counts = defaultdict(int)
for ki in extracted_items:
    kind_counts[ki['kind']] += 1

print("Items by kind:")
for kind in sorted(kind_counts.keys()):
    print("  {}: {}".format(kind, kind_counts[kind]))

print()

# Ambiguous items
ambiguous_items = [ki for ki in extracted_items if ki['confidence'] < 0.5]
print("Ambiguous items (confidence < 0.5): {}".format(len(ambiguous_items)))

print()

# =========================================================================
# STEP 6: Validation
# =========================================================================

print("-" * 70)
print("STEP 6: VALIDATION")
print("-" * 70)
print()

validation_errors = []

# Check 1: Every extracted item has source provenance
for ki in extracted_items:
    if not ki.get('source_id') or not ki.get('source_segment_ids'):
        validation_errors.append("KI {} missing source provenance".format(ki['knowledge_item_id']))

# Check 2: Every source segment referenced actually exists
segment_ids_in_transcript = {seg['segment_id'] for seg in segments}
for ki in extracted_items:
    for ref_id in ki['source_segment_ids']:
        if ref_id not in segment_ids_in_transcript:
            validation_errors.append("KI {} references non-existent segment {}".format(
                ki['knowledge_item_id'], ref_id))

# Check 3: No raw transcript text was modified
for ki in extracted_items:
    reconstructed = " ".join([
        seg['text'] for seg in segments if seg['segment_id'] in ki['source_segment_ids']
    ])
    if reconstructed != ki['raw_source_text']:
        # Allow minor differences from whitespace
        if reconstructed.replace("  ", " ") != ki['raw_source_text'].replace("  ", " "):
            validation_errors.append("KI {} raw text mismatch".format(ki['knowledge_item_id']))

# Check 4: No Serum parameter mappings
for ki in extracted_items:
    if any(param in ki['extracted_statement'].lower() for param in [
        'Filter1.Cutoff', 'OSC1.Level', 'Env1.Attack', 'kParamFreq'
    ]):
        validation_errors.append("KI {} contains explicit parameter mapping".format(
            ki['knowledge_item_id']))

if validation_errors:
    print("[FAIL] {} validation errors:".format(len(validation_errors)))
    for error in validation_errors[:10]:
        print("  - {}".format(error))
else:
    print("[OK] All validation checks passed")

print()

# =========================================================================
# STEP 7: Create extraction artifact
# =========================================================================

print("-" * 70)
print("STEP 7: CREATE EXTRACTION ARTIFACT")
print("-" * 70)
print()

extraction_artifact = {
    "version": "1.0",
    "source_id": source_record['source_id'],
    "extraction_metadata": {
        "source_transcript_segments": len(segments),
        "semantic_units_identified": len(semantic_units),
        "knowledge_items_extracted": len(extracted_items),
        "segments_covered": len(covered_segment_ids),
        "coverage_percentage": coverage_pct,
        "items_by_kind": dict(kind_counts),
        "ambiguous_items": len(ambiguous_items),
        "validation_errors": len(validation_errors),
    },
    "extracted_knowledge_items": extracted_items,
}

output_path = "serum2/knowledge/yt_f507169bd7cb_semantic_extraction.json"

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(extraction_artifact, f, indent=2, ensure_ascii=False)

print("[OK] Extraction artifact written: {}".format(output_path))

# Count file size
import os
file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
print("  Size: {:.1f} MB".format(file_size_mb))

print()

# =========================================================================
# STEP 8: Extract report
# =========================================================================

print("=" * 70)
print("SEMANTIC EXTRACTION REPORT")
print("=" * 70)
print()

print("COVERAGE:")
print("  Total segments: {}".format(len(segments)))
print("  Extracted items: {}".format(len(extracted_items)))
print("  Segments covered: {} ({:.1f}%)".format(
    len(covered_segment_ids), coverage_pct))
print("  Uncovered segments: {} ({:.1f}%)".format(
    len(segments) - len(covered_segment_ids),
    100.0 - coverage_pct
))
print()

print("ITEMS BY KIND:")
for kind in sorted(kind_counts.keys()):
    pct = 100.0 * kind_counts[kind] / len(extracted_items) if extracted_items else 0
    print("  {}: {} ({:.1f}%)".format(kind, kind_counts[kind], pct))
print()

print("EXTRACTION STATUS:")
status_counts = defaultdict(int)
for ki in extracted_items:
    status_counts[ki['extraction_status']] += 1

for status in sorted(status_counts.keys()):
    print("  {}: {}".format(status, status_counts[status]))
print()

print("AMBIGUOUS ITEMS: {}".format(len(ambiguous_items)))
print()

print("VALIDATION:")
print("  Errors: {}".format(len(validation_errors)))
if validation_errors:
    print("  Issues:")
    for error in validation_errors[:5]:
        print("    - {}".format(error))
else:
    print("  Status: ALL CHECKS PASSED")

print()

# =========================================================================
# EXAMPLE ITEMS BY KIND
# =========================================================================

print("=" * 70)
print("EXAMPLE ITEMS BY KIND")
print("=" * 70)
print()

example_kinds = ['PROCEDURE', 'OPERATION', 'RELATIONSHIP', 'PROPERTY']

for kind in example_kinds:
    examples = [ki for ki in extracted_items if ki['kind'] == kind]
    if examples:
        ex = examples[0]
        print("{}:".format(kind))
        print("  Time: {:.1f}s - {:.1f}s".format(
            ex['start_time_sec'], ex['end_time_sec']))
        print("  Segments: {}".format(len(ex['source_segment_ids'])))
        print("  Text: {}...".format(ex['extracted_statement'][:100]))
        print()

print()
print("EXTRACTION COMPLETE")
print()
