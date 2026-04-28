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



def render_text_clips(*args, **kwargs):
    raise NotImplementedError("MoviePy/TextClip rendering is no longer supported. Use ASS/FFmpeg rendering instead.")
