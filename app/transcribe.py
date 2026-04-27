"""
Whisper transcription helpers (word-level timestamps) using faster-whisper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import sys

from faster_whisper import WhisperModel

# Load lightweight model once; adjust model size/compute_type as needed.
print("[TRANSCRIBE] Loading Whisper model (base, CPU, int8)...", file=sys.stderr)
_model = WhisperModel("base", device="cpu", compute_type="int8")
print("[TRANSCRIBE] Whisper model loaded successfully", file=sys.stderr)


def transcribe_audio(audio_path: str | Path, language: Optional[str] = None) -> Dict:
    """
    Transcribe audio and return raw text plus word-level timings.
    Structure:
    {
        "text": "...",
        "words": [{"word": str, "start": float, "end": float}, ...]
    }
    """
    print(f"[TRANSCRIBE] Starting transcription - Audio: {audio_path}, Language: {language}", file=sys.stderr)
    segments, _ = _model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
    )
    print(f"[TRANSCRIBE] Transcription segments received, processing...", file=sys.stderr)

    all_words: List[Dict] = []
    full_text_parts: List[str] = []
    seg_count = 0
    for seg in segments:
        seg_count += 1
        print(f"[TRANSCRIBE] Segment {seg_count}: {seg.text.strip()[:80]}", file=sys.stderr)
        full_text_parts.append(seg.text.strip())
        if seg.words:
            print(f"[TRANSCRIBE]   Processing {len(seg.words)} words from segment {seg_count}...", file=sys.stderr)
            for word_idx, w in enumerate(seg.words, 1):
                word_data = {
                    "word": w.word.strip(),
                    "start": float(w.start),
                    "end": float(w.end),
                }
                print(f"[TRANSCRIBE]   Word {word_idx}: '{word_data['word']}' ({word_data['start']:.2f}s - {word_data['end']:.2f}s)", file=sys.stderr)
                all_words.append(word_data)

    # Fallback to segment-level timings if word-level missing
    if not all_words:
        print(f"[TRANSCRIBE] No word-level timings found, using segment-level fallback...", file=sys.stderr)
        tmp_words = []
        for seg_idx, seg in enumerate(segments, 1):
            tmp_words.append(
                {
                    "word": seg.text.strip(),
                    "start": float(seg.start),
                    "end": float(seg.end),
                }
            )
            print(f"[TRANSCRIBE] Segment {seg_idx}: {seg.text.strip()[:80]}", file=sys.stderr)
        all_words = tmp_words

    full_text = " ".join(full_text_parts).strip()
    print(f"[TRANSCRIBE] Transcription complete - Total words: {len(all_words)}, Full text: {full_text[:100]}...", file=sys.stderr)
    return {"text": full_text, "words": all_words}
