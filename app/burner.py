"""
Caption rendering using FFmpeg + ASS subtitles or MoviePy TextClips.
Supports both lightweight subtitle rendering and high-quality text clip rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import tempfile
import time
import os
import sys

from app.ass_renderer import build_ass
from app.text_clip_renderer import render_text_clips


def render_captions(
    video_path: str | Path,
    captions: List[Dict],
    output_path: str | Path,
    pos_x: float = 0.5,
    pos_y: float = 0.5,
    fast_mode: bool = True,
    target_width: int = 1280,
    font_name: str = "Arial",
    font_size: int = 110,
    font_color: str = "#00FFFF",
    style_preset: str = "classic",
    render_method: str = "ass",
) -> Dict:
    """
    Burn captions onto video using ASS subtitles or MoviePy TextClips.
    
    Args:
        video_path: Path to input video
        captions: List of caption dictionaries
        output_path: Path for output video
        pos_x: Horizontal position (0-1)
        pos_y: Vertical position (0-1)
        fast_mode: Use ultrafast preset (ASS only)
        target_width: Target width for scaling (ASS only)
        font_name: Font family name
        font_size: Font size in pixels
        font_color: Color in hex format (#RRGGBB)
        style_preset: Style preset (classic, bold, outlined)
        render_method: "ass" (subtitles, fast) or "textclip" (graphics, high quality)
    
    Returns dict with output path and duration seconds.
    """
    print(f"[BURNER] Starting caption rendering - Method: {render_method}, Video: {video_path}", file=sys.stderr)
    
    # Remove MoviePy TextClip renderer (not supported)
    if render_method == "textclip":
        raise NotImplementedError("MoviePy/TextClip rendering is no longer supported. Use render_method='ass' for FFmpeg-based rendering.")
    
    # Default to ASS subtitle rendering
    return _render_ass_captions(
        video_path,
        captions,
        output_path,
        pos_x=pos_x,
        pos_y=pos_y,
        fast_mode=fast_mode,
        target_width=target_width,
        font_name=font_name,
        font_size=font_size,
        font_color=font_color,
        style_preset=style_preset,
    )


def _render_ass_captions(
    video_path: str | Path,
    captions: List[Dict],
    output_path: str | Path,
    pos_x: float = 0.5,
    pos_y: float = 0.5,
    fast_mode: bool = True,
    target_width: int = 1280,
    font_name: str = "Arial",
    font_size: int = 110,
    font_color: str = "#00FFFF",
    style_preset: str = "classic",
) -> Dict:
    """Internal function for ASS subtitle rendering."""
    print(f"[BURNER] Starting ASS subtitle rendering - Video: {video_path}, Output: {output_path}", file=sys.stderr)
    started_at = time.perf_counter()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[BURNER] Output directory ready: {output_path.parent}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as td:
        print(f"[BURNER] Using temporary directory: {td}", file=sys.stderr)
        ass_path = Path(td) / "captions.ass"
        print(f"[BURNER] Building ASS subtitle file...", file=sys.stderr)
        build_ass(
            captions,
            ass_path,
            pos_xy=(pos_x, pos_y),
            font_name=font_name,
            font_size=font_size,
            font_color=font_color,
            style_preset=style_preset,
        )
        
        # Validate ASS file was created
        print(f"[BURNER] Validating ASS file creation...", file=sys.stderr)
        if not os.path.exists(ass_path):
            raise FileNotFoundError(f"ASS subtitle file was not created: {ass_path}")

        vf_parts = []
        if fast_mode and target_width:
            print(f"[BURNER] Fast mode enabled - Scaling to {target_width}px width", file=sys.stderr)
            # FIXED: Escape comma in min() function
            vf_parts.append(f"scale=min({target_width}\\,iw):-2")
        
        # FIXED: Properly escape Windows path for FFmpeg filtergraph
        print(f"[BURNER] Preparing FFmpeg filtergraph...", file=sys.stderr)
        # Convert backslashes to forward slashes and escape colons
        escaped_path = ass_path.as_posix().replace(":", "\\:")
        # FIXED: Remove filename= parameter, use direct path
        vf_parts.append(f"subtitles='{escaped_path}'")
        vf = ",".join(vf_parts)
        print(f"[BURNER] Filtergraph: {vf}", file=sys.stderr)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast" if fast_mode else "medium",
            "-crf",
            "18",
            "-c:a",
            "copy",
            str(output_path),
        ]
        
        print(f"[BURNER] Executing FFmpeg command...", file=sys.stderr)
        print(f"[BURNER] Command: {' '.join(cmd)}", file=sys.stderr)
        try:
            print(f"[BURNER] FFmpeg encoding started...", file=sys.stderr)
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[BURNER] FFmpeg encoding completed successfully", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            # Provide detailed error information
            print(f"[BURNER] FFmpeg ERROR - Exit code: {e.returncode}", file=sys.stderr)
            error_msg = f"FFmpeg failed with exit code {e.returncode}"
            if e.stderr:
                error_msg += f"\nStderr: {e.stderr.decode()}"
                print(f"[BURNER] FFmpeg stderr: {e.stderr.decode()[:200]}", file=sys.stderr)
            if e.stdout:
                error_msg += f"\nStdout: {e.stdout.decode()}"
                print(f"[BURNER] FFmpeg stdout: {e.stdout.decode()[:200]}", file=sys.stderr)
            raise RuntimeError(error_msg) from e

    duration = time.perf_counter() - started_at
    print(f"[BURNER] ASS rendering completed in {duration:.2f}s - Output: {output_path}", file=sys.stderr)
    return {"output_path": output_path, "burn_seconds": duration}
