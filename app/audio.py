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
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[AUDIO] Audio extraction completed successfully - {audio_path}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"[AUDIO] ERROR - FFmpeg extraction failed with code {e.returncode}", file=sys.stderr)
        raise
    return audio_path


def ensure_storage_dirs(base: str | Path) -> tuple[Path, Path]:
    """Create uploads/outputs under base and return them."""
    base = Path(base)
    uploads = base / "storage" / "uploads"
    outputs = base / "storage" / "outputs"
    uploads.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    return uploads, outputs
