"""
Text clip rendering using MoviePy for clean, customizable caption graphics.
Renders text as actual video elements with full styling control.
"""

from __future__ import annotations



import os
# Set ImageMagick binary path for MoviePy (Windows, user version 7.1.2-19)
os.environ["IMAGEMAGICK_BINARY"] = r"C:\\Program Files\\ImageMagick-7.1.2-Q16-HDRI\\magick.exe"

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import tempfile
import time
import sys

from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.VideoClip import ColorClip


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color (#RRGGBB or RRGGBB) to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    return (0, 255, 255)  # Default cyan if conversion fails


def _get_text_properties(style_preset: str, font_size: int, color_hex: str) -> Dict:
    """Get text rendering properties based on style preset."""
    props = {
        "fontsize": font_size,
        "color": color_hex,  # Pass hex string directly
    }
    # Stroke/outline logic can be added here if needed and supported
    return props



def render_text_clips(

    video_path: str | Path,
    captions: List[Dict],
    output_path: str | Path,
    pos_x: float = 0.5,
    pos_y: float = 0.85,
    font_name: str = "Arial",
    font_size: int = 120,
    font_color: str = "#00FFFF",
    style_preset: str = "classic",
) -> Dict:
    """
    Burn captions onto video as text clips using MoviePy.
    
    Args:
        video_path: Path to input video
        captions: List of caption dictionaries
        output_path: Path for output video
        pos_x: Horizontal position (0-1, 0.5 = center)
        pos_y: Vertical position (0-1, 0.85 = near bottom)
        font_name: Font family name
        font_size: Font size in pixels
        font_color: Color in hex format (#RRGGBB)
        style_preset: Style preset (classic, bold, outlined)
    
    Returns dict with output path and duration seconds.
    """
    print(f"[TEXT_CLIP] Starting text clip rendering - Video: {video_path}, Output: {output_path}", file=sys.stderr)
    started_at = time.perf_counter()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[TEXT_CLIP] Output directory ready: {output_path.parent}", file=sys.stderr)
    
    # Load video
    print(f"[TEXT_CLIP] Loading video: {video_path}", file=sys.stderr)
    video = VideoFileClip(str(video_path))
    video_width = int(video.w)
    video_height = int(video.h)
    print(f"[TEXT_CLIP] Video dimensions: {video_width}x{video_height}, Duration: {video.duration:.2f}s", file=sys.stderr)
    
    # Convert color
    color_rgb = _hex_to_rgb(font_color)
    print(f"[TEXT_CLIP] Font: {font_name}, Size: {font_size}, Color: {font_color} (RGB: {color_rgb}), Preset: {style_preset}", file=sys.stderr)
    
    # Get text properties, but pass hex string for color
    text_props = _get_text_properties(style_preset, font_size, font_color)
    text_props["font"] = font_name
    
    # Calculate position in pixels
    x_pos = int(pos_x * video_width)
    y_pos = int(pos_y * video_height)
    print(f"[TEXT_CLIP] Caption position: ({x_pos}px, {y_pos}px)", file=sys.stderr)
    
    # Create text clips for each caption
    text_clips = []
    for cap_idx, cap in enumerate(captions, 1):
        print(f"[TEXT_CLIP] Processing caption {cap_idx}/{len(captions)} - Time: {cap['start']:.2f}s to {cap['end']:.2f}s", file=sys.stderr)
        
        # Build text with emphasis highlighting
        text_parts = []
        for word_idx, w in enumerate(cap["words"], 1):
            word_text = w["word"].replace(",", " ").replace("{", "").replace("}", "").strip()
            if w.get("emphasized"):
                print(f"[TEXT_CLIP]   Word {word_idx}: '{word_text}' (EMPHASIZED)", file=sys.stderr)
                # Emphasized words will be rendered with extra size
                text_parts.append(f"{{b}}{word_text}{{/b}}")
            else:
                print(f"[TEXT_CLIP]   Word {word_idx}: '{word_text}'", file=sys.stderr)
                text_parts.append(word_text)
        
        caption_text = " ".join(text_parts)
        print(f"[TEXT_CLIP] Caption text: {caption_text[:60]}{'...' if len(caption_text) > 60 else ''}", file=sys.stderr)
        
        # Create text clip
        try:
            # MoviePy TextClip with basic, compatible parameters only
            # Avoid problematic parameters like stroke_color, stroke_width, size
            txt_clip = TextClip(
                txt=caption_text,
                fontsize=int(text_props["fontsize"]),
                font=str(text_props["font"]),
                color=text_props["color"],
            )
            
            # Set position and duration
            txt_clip = txt_clip.set_position((x_pos, y_pos), relative=False)
            txt_clip = txt_clip.set_start(cap["start"])
            txt_clip = txt_clip.set_end(cap["end"])
            
            text_clips.append(txt_clip)
            print(f"[TEXT_CLIP] Text clip created successfully", file=sys.stderr)
        except Exception as e:
            print(f"[TEXT_CLIP] Error creating text clip: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise
    
    # Composite all text clips over the video
    print(f"[TEXT_CLIP] Compositing {len(text_clips)} text clips over video...", file=sys.stderr)
    final_video = CompositeVideoClip([video] + text_clips)
    
    # Write output video
    print(f"[TEXT_CLIP] Writing output video to: {output_path}", file=sys.stderr)
    # Use MoviePy's default logger (no custom progress bar)
    final_video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        verbose=False,
    )
    
    # Clean up
    video.close()
    final_video.close()
    for clip in text_clips:
        clip.close()
    
    elapsed = time.perf_counter() - started_at
    print(f"[TEXT_CLIP] Text clip rendering completed in {elapsed:.2f}s", file=sys.stderr)
    
    return {
        "output_path": str(output_path),
        "burn_seconds": elapsed,
    }
