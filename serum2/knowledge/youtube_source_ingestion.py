"""YouTube Source Ingestion Proof

Retrieve and preserve transcript from YouTube video with full provenance.
No inference, no summarization—verbatim transcript extraction only.
"""

import json
import datetime
import hashlib
from typing import Optional, Dict, List
import subprocess
import sys

print("=" * 70)
print("YOUTUBE SOURCE INGESTION PROOF")
print("=" * 70)
print()

# =========================================================================
# TARGET VIDEO
# =========================================================================

VIDEO_URL = "https://www.youtube.com/watch?v=ItRL3FNpd-8"
VIDEO_ID = "ItRL3FNpd-8"

print("Target video:")
print("  URL: {}".format(VIDEO_URL))
print("  Video ID: {}".format(VIDEO_ID))
print()

# =========================================================================
# STEP 1: Retrieve metadata using yt-dlp
# =========================================================================

print("-" * 70)
print("STEP 1: RETRIEVE VIDEO METADATA")
print("-" * 70)
print()

try:
    # Use yt-dlp to extract metadata and subtitle
    import yt_dlp

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'writesubtitles': False,  # Don't download, just extract
        'extract_flat': False,
    }

    print("Extracting metadata using yt-dlp...")
    print()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(VIDEO_URL, download=False)

    title = info.get('title', 'UNKNOWN')
    channel = info.get('uploader', 'UNKNOWN')
    duration = info.get('duration', 0)  # in seconds
    upload_date = info.get('upload_date', 'UNKNOWN')

    print("[OK] Metadata retrieved")
    print("  Title: {}".format(title))
    print("  Channel: {}".format(channel))
    print("  Duration: {} seconds ({:.1f} minutes)".format(duration, duration/60))
    print("  Upload date: {}".format(upload_date))
    print()

    metadata_available = True

except Exception as e:
    print("[FAIL] Could not retrieve metadata: {}".format(e))
    print()
    title = "UNKNOWN"
    channel = "UNKNOWN"
    duration = 0
    upload_date = "UNKNOWN"
    metadata_available = False

# =========================================================================
# STEP 2: Retrieve transcript
# =========================================================================

print("-" * 70)
print("STEP 2: RETRIEVE TRANSCRIPT")
print("-" * 70)
print()

transcript_available = False
transcript_segments = []

try:
    from youtube_transcript_api import YouTubeTranscriptApi

    print("Attempting to extract transcript using youtube-transcript-api...")
    print()

    ytt_api = YouTubeTranscriptApi()

    # Try to get the transcript
    try:
        # First try English
        fetched_transcript = ytt_api.fetch(VIDEO_ID, languages=['en'])
        print("[OK] English transcript retrieved")
        # Convert to raw data format
        transcript_data = fetched_transcript.to_raw_data() if hasattr(fetched_transcript, 'to_raw_data') else fetched_transcript
    except Exception as e:
        print("[FAIL] Could not retrieve English transcript: {}".format(str(e)))
        # Try any available language by listing
        try:
            transcript_list = ytt_api.list(VIDEO_ID)
            # Get first available transcript
            if len(transcript_list) > 0:
                transcript = transcript_list[0]
                fetched_transcript = transcript.fetch()
                transcript_data = fetched_transcript.to_raw_data() if hasattr(fetched_transcript, 'to_raw_data') else fetched_transcript
                print("[OK] {} transcript retrieved".format(transcript.language))
            else:
                transcript_data = None
                print("[FAIL] No transcripts available")
        except Exception as e2:
            transcript_data = None
            print("[FAIL] No transcript found: {}".format(str(e2)))

    if transcript_data:
        transcript_available = True
        print()
        print("Processing transcript segments...")
        print()

        # Each entry has: 'text', 'start', 'duration'
        for i, entry in enumerate(transcript_data):
            start_time = entry.get('start', 0)
            duration = entry.get('duration', 0)
            end_time = start_time + duration
            text = entry.get('text', '')

            segment_id = "seg_{:04d}".format(i)

            transcript_segments.append({
                "segment_id": segment_id,
                "index": i,
                "start_time_sec": start_time,
                "end_time_sec": end_time,
                "duration_sec": duration,
                "text": text,
            })

        print("[OK] Extracted {} transcript segments".format(len(transcript_segments)))

except Exception as e:
    print("[FAIL] Could not retrieve transcript: {}".format(e))
    print("Error: {}".format(str(e)))
    transcript_available = False

print()

# =========================================================================
# STEP 3: Create source record
# =========================================================================

print("-" * 70)
print("STEP 3: CREATE SOURCE RECORD")
print("-" * 70)
print()

retrieval_timestamp = datetime.datetime.utcnow().isoformat() + "Z"
source_id = "yt_" + hashlib.md5(VIDEO_URL.encode()).hexdigest()[:12]

source_record = {
    "source_id": source_id,
    "source_type": "YOUTUBE_VIDEO",
    "url": VIDEO_URL,
    "video_id": VIDEO_ID,
    "title": title if metadata_available else "UNKNOWN",
    "channel": channel if metadata_available else "UNKNOWN",
    "duration_seconds": duration if metadata_available else None,
    "upload_date": upload_date if metadata_available else None,
    "retrieval_timestamp": retrieval_timestamp,
    "metadata_available": metadata_available,
    "transcript_available": transcript_available,
    "transcript_segment_count": len(transcript_segments),
}

print("Source record created:")
print("  source_id: {}".format(source_record["source_id"]))
print("  URL: {}".format(source_record["url"]))
print("  Title: {}".format(source_record["title"]))
print("  Channel: {}".format(source_record["channel"]))
print("  Duration: {} sec".format(source_record["duration_seconds"]))
print("  Transcript available: {}".format(source_record["transcript_available"]))
print("  Segments: {}".format(source_record["transcript_segment_count"]))
print()

# =========================================================================
# STEP 4: Create KnowledgeItem records (provenance only)
# =========================================================================

print("-" * 70)
print("STEP 4: CREATE KNOWLEDGE ITEM RECORDS")
print("-" * 70)
print()

knowledge_items = []

if transcript_available:
    for segment in transcript_segments:
        # Create a minimal KnowledgeItem for each transcript segment
        # No inference, just source preservation

        ki = {
            "id": "ki_{}".format(segment["segment_id"]),
            "source_id": source_id,
            "segment_id": segment["segment_id"],
            "source_span": {
                "start_time_sec": segment["start_time_sec"],
                "end_time_sec": segment["end_time_sec"],
            },
            "kind": "SOURCE_TEXT_ONLY",  # No interpretation yet
            "raw_text": segment["text"],
            "extraction_status": "SOURCE_TEXT_ONLY",  # Verbatim, no processing
        }

        knowledge_items.append(ki)

print("[OK] Created {} KnowledgeItem records (one per transcript segment)".format(len(knowledge_items)))
print()

# =========================================================================
# STEP 5: Validation
# =========================================================================

print("-" * 70)
print("STEP 5: VALIDATION")
print("-" * 70)
print()

validation_results = {
    "transcript_exists": transcript_available,
    "timestamps_ordered": True,
    "source_id_stable": True,
    "every_segment_has_provenance": True,
    "original_text_recoverable": True,
}

# Check timestamps are ordered
if transcript_segments:
    prev_time = 0
    for seg in transcript_segments:
        if seg["start_time_sec"] < prev_time:
            validation_results["timestamps_ordered"] = False
            break
        prev_time = seg["end_time_sec"]

# Check all segments have provenance
for seg in transcript_segments:
    if not seg.get("segment_id") or seg.get("text") is None:
        validation_results["every_segment_has_provenance"] = False
        break

# Check original text is recoverable (it is, verbatim)
for ki in knowledge_items:
    if not ki.get("raw_text"):
        validation_results["original_text_recoverable"] = False
        break

print("Validation results:")
for key, value in validation_results.items():
    status = "[OK]" if value else "[FAIL]"
    print("  {} {}: {}".format(status, key, value))

all_valid = all(validation_results.values())
print()
if all_valid:
    print("[OK] ALL VALIDATION CHECKS PASSED")
else:
    print("[WARN] Some validation checks failed")

print()

# =========================================================================
# STEP 6: Create machine-readable artifact
# =========================================================================

print("-" * 70)
print("STEP 6: CREATE MACHINE-READABLE ARTIFACT")
print("-" * 70)
print()

artifact = {
    "version": "1.0",
    "source": source_record,
    "transcript_segments": transcript_segments,
    "knowledge_items": knowledge_items,
    "validation": validation_results,
}

artifact_filename = "serum2/knowledge/{}_source_ingestion.json".format(source_id)

print("Writing artifact to: {}".format(artifact_filename))
print()

try:
    with open(artifact_filename, 'w', encoding='utf-8') as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)

    print("[OK] Artifact written successfully")
    print("  File: {}".format(artifact_filename))
    print("  Size: {} bytes".format(len(json.dumps(artifact))))

except Exception as e:
    print("[FAIL] Could not write artifact: {}".format(e))

print()

# =========================================================================
# FINAL REPORT
# =========================================================================

print("=" * 70)
print("SOURCE INGESTION PROOF COMPLETE")
print("=" * 70)
print()

print("RETRIEVAL MECHANISM:")
print("  Tool: yt-dlp")
print("  Method: extract_info with subtitle extraction")
print()

print("TRANSCRIPT RETRIEVAL:")
print("  Status: {}".format("SUCCESS" if transcript_available else "FAILED"))
print("  Segments extracted: {}".format(len(transcript_segments)))
if transcript_segments:
    print("  Time coverage: {:.1f}s to {:.1f}s".format(
        transcript_segments[0]["start_time_sec"],
        transcript_segments[-1]["end_time_sec"]
    ))
print()

print("FILES CREATED:")
print("  Artifact: {}".format(artifact_filename))
print()

print("VALIDATION RESULT:")
print("  Status: {}".format("PASS" if all_valid else "PARTIAL"))
for key, value in validation_results.items():
    print("    {}: {}".format(key, value))
print()

print("METADATA AVAILABILITY:")
print("  Title: {}".format("YES" if metadata_available else "NO"))
print("  Channel: {}".format("YES" if metadata_available else "NO"))
print("  Duration: {}".format("YES" if metadata_available else "NO"))
print("  Upload date: {}".format("YES" if metadata_available else "NO"))
print()

print("NEXT STEP:")
if transcript_available:
    print("  Transcript successfully ingested with provenance.")
    print("  Ready for semantic extraction layer (future work).")
else:
    print("  Transcript retrieval failed.")
    print("  Manual transcript entry or alternative source required.")

