"""
Whisper transcription helpers (word-level timestamps) using faster-whisper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from faster_whisper import WhisperModel

# Load lightweight model once; adjust model size/compute_type as needed.
_model = WhisperModel("base", device="cpu", compute_type="int8")


def transcribe_audio(audio_path: str | Path, language: Optional[str] = None) -> Dict:
    """
    Transcribe audio and return raw text plus word-level timings.
    Structure:
    {
        "text": "...",
        "words": [{"word": str, "start": float, "end": float}, ...]
    }
    """
    segments, _ = _model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
    )

    all_words: List[Dict] = []
    full_text_parts: List[str] = []
    for seg in segments:
        full_text_parts.append(seg.text.strip())
        if seg.words:
            for w in seg.words:
                all_words.append(
                    {
                        "word": w.word.strip(),
                        "start": float(w.start),
                        "end": float(w.end),
                    }
                )

    # Fallback to segment-level timings if word-level missing
    if not all_words:
        tmp_words = []
        for seg in segments:
            tmp_words.append(
                {
                    "word": seg.text.strip(),
                    "start": float(seg.start),
                    "end": float(seg.end),
                }
            )
        all_words = tmp_words

    return {"text": " ".join(full_text_parts).strip(), "words": all_words}
