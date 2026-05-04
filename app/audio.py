"""
Audio extraction utilities.
FFmpeg is required on PATH.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional
import time
import os
import sys

from app.file_validator import validate_extracted_audio, FileValidationError


class AudioExtractionError(Exception):
    """Raised when audio extraction fails."""
    pass


def extract_audio(video_path: str | Path, output_dir: str | Path) -> Path:
    """
    Extract audio from a video file using ffmpeg.

    Returns the path to the extracted WAV file.
    """
    print(f"[AUDIO] Starting audio extraction - Video: {video_path}", file=sys.stderr)
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[AUDIO] Output directory ready: {output_dir}", file=sys.stderr)
    
    audio_path = output_dir / f"{video_path.stem}_{int(time.time()*1000)}.wav"
    print(f"[AUDIO] Output audio file: {audio_path}", file=sys.stderr)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    print(f"[AUDIO] Executing FFmpeg extraction command...", file=sys.stderr)
    try:
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
        )
        
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
            error_msg = (
                f"FFmpeg extraction failed with code {result.returncode}. "
                f"The video file may be corrupted or in an unsupported format. "
                f"Details: {stderr[:300]}"
            )
            print(f"[AUDIO] ERROR - {error_msg}", file=sys.stderr)
            raise AudioExtractionError(error_msg)
        
        # Validate extracted audio
        try:
            validate_extracted_audio(audio_path, min_duration=0.5)
            print(f"[AUDIO] Audio extraction completed and validated - {audio_path}", file=sys.stderr)
        except FileValidationError as e:
            print(f"[AUDIO] ERROR - Audio validation failed: {e}", file=sys.stderr)
            # Clean up corrupted audio file
            if audio_path.exists():
                audio_path.unlink()
                print(f"[AUDIO] Cleaned up corrupted audio file", file=sys.stderr)
            raise AudioExtractionError(str(e))
            
    except subprocess.TimeoutExpired:
        error_msg = "Audio extraction timed out (exceeded 5 minutes). Video file may be corrupted."
        print(f"[AUDIO] ERROR - {error_msg}", file=sys.stderr)
        if audio_path.exists():
            audio_path.unlink()
        raise AudioExtractionError(error_msg)
    except FileNotFoundError:
        error_msg = "FFmpeg not found. Please ensure FFmpeg is installed and in PATH."
        print(f"[AUDIO] ERROR - {error_msg}", file=sys.stderr)
        raise AudioExtractionError(error_msg)
    return audio_path


def ensure_storage_dirs(base: str | Path) -> tuple[Path, Path]:
    """Create uploads/outputs under base and return them."""
    base = Path(base)
    uploads = base / "storage" / "uploads"
    outputs = base / "storage" / "outputs"
    uploads.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    return uploads, outputs
