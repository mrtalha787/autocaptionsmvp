"""
Generate ASS subtitle scripts for fast FFmpeg burning.
Supports customizable fonts, colors, sizes, and style presets.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sys


def _hex_to_bgr(hex_color: str) -> str:
    """Convert hex color (e.g., #RRGGBB or RRGGBB) to BGR format for ASS."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        bgr = b + g + r
        return f"&H00{bgr.upper()}"
    return "&H00FFFF"  # Default to cyan/yellow if conversion fails


def _get_style_preset(preset: str, fontsize: int, color_bgr: str, fontname: str) -> Dict:
    """Get style dictionary based on preset name."""
    base_style = {
        "Name": "Default",
        "Fontname": fontname,
        "Fontsize": fontsize,
        "PrimaryColour": color_bgr,
        "SecondaryColour": "&H00FFFFFF",
        "BackColour": "&H00000000",
        "Bold": 0,
        "Italic": 0,
        "Underline": 0,
        "StrikeOut": 0,
        "ScaleX": 100,
        "ScaleY": 100,
        "Spacing": 0,
        "Angle": 0,
        "Alignment": 2,  # bottom-center
        "MarginL": 20,
        "MarginR": 20,
        "MarginV": 40,
        "Encoding": 0,
    }
    
    if preset == "bold":
        base_style["Bold"] = 1
        base_style["BorderStyle"] = 1
        base_style["Outline"] = 3
        base_style["Shadow"] = 2
    elif preset == "outlined":
        base_style["BorderStyle"] = 1
        base_style["Outline"] = 4
        base_style["Shadow"] = 0
        base_style["OutlineColour"] = "&H00000000"
    else:  # classic
        base_style["BorderStyle"] = 1
        base_style["Outline"] = 2
        base_style["Shadow"] = 1
    
    base_style["OutlineColour"] = "&H00000000"  # Black outline
    return base_style


PLAY_RES_X = 1280
PLAY_RES_Y = 720


def _fmt_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(text: str) -> str:
    return text.replace(",", " ").replace("{", "").replace("}", "").strip()


def build_ass(
    captions: List[Dict],
    path: Path,
    pos_xy: Optional[Tuple[float, float]] = None,
    font_name: str = "Arial",
    font_size: int = 120,
    font_color: str = "#00FFFF",
    style_preset: str = "classic",
) -> Path:
    """
    Build ASS subtitle file with customizable styling.
    
    Args:
        captions: List of caption dictionaries
        path: Output file path
        pos_xy: Optional (x, y) position tuple (0-1 range)
        font_name: Font family name
        font_size: Font size in pixels
        font_color: Color in hex format (#RRGGBB)
        style_preset: Style preset (classic, bold, outlined)
    """
    print(f"[ASS_RENDERER] Building ASS file - Font: {font_name}, Size: {font_size}, Color: {font_color}, Preset: {style_preset}", file=sys.stderr)
    
    # Convert hex color to BGR format
    color_bgr = _hex_to_bgr(font_color)
    
    # Get style based on preset
    style = _get_style_preset(style_preset, font_size, color_bgr, font_name)
    
    lines = []
    lines.append("[Script Info]")
    lines.append("ScriptType: v4.00+")
    lines.append("WrapStyle: 2")
    lines.append("ScaledBorderAndShadow: yes")
    lines.append(f"PlayResX: {PLAY_RES_X}")
    lines.append(f"PlayResY: {PLAY_RES_Y}")
    lines.append("")
    lines.append("[V4+ Styles]")
    fields = [
        "Name",
        "Fontname",
        "Fontsize",
        "PrimaryColour",
        "SecondaryColour",
        "OutlineColour",
        "BackColour",
        "Bold",
        "Italic",
        "Underline",
        "StrikeOut",
        "ScaleX",
        "ScaleY",
        "Spacing",
        "Angle",
        "BorderStyle",
        "Outline",
        "Shadow",
        "Alignment",
        "MarginL",
        "MarginR",
        "MarginV",
        "Encoding",
    ]
    fmt_line = ",".join(["Style"] + fields)
    lines.append(fmt_line)
    style_line = ",".join(str(style.get(f, 0)) for f in fields)
    lines.append(style_line)
    lines.append("")
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    for cap_idx, cap in enumerate(captions, 1):
        print(f"[ASS_RENDERER] Processing caption {cap_idx}/{len(captions)} - Time: {cap['start']:.2f}s to {cap['end']:.2f}s", file=sys.stderr)
        text_parts = []
        for word_idx, w in enumerate(cap["words"], 1):
            txt = _clean(w["word"])
            if w.get("emphasized"):
                print(f"[ASS_RENDERER]   Word {word_idx}: '{txt}' (EMPHASIZED)", file=sys.stderr)
                # Emphasized words get bold + larger size
                emph_size = font_size + 12
                text_parts.append(r"{{\\b1\\fs{}}}{}{{\\b0}}".format(emph_size, txt))
            else:
                print(f"[ASS_RENDERER]   Word {word_idx}: '{txt}'", file=sys.stderr)
                text_parts.append(txt)
        
        line_text = r"{{\\c{}}}".format(color_bgr) + " ".join(text_parts)
        print(f"[ASS_RENDERER] Caption text: {line_text[:60]}{'...' if len(line_text) > 60 else ''}", file=sys.stderr)
        
        if pos_xy:
            x = int(pos_xy[0] * PLAY_RES_X)
            y = int(pos_xy[1] * PLAY_RES_Y)
            line_text = r"{{\\pos({},{})}}{}".format(x, y, line_text)
        
        start = _fmt_time(cap["start"])
        end = _fmt_time(cap["end"])
        evt = f"Dialogue: 0,{start},{end},{style['Name']},,0,0,0,,{line_text}"
        lines.append(evt)

    print(f"[ASS_RENDERER] Writing ASS file with {len(lines)} lines to {path}", file=sys.stderr)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[ASS_RENDERER] ASS file created successfully", file=sys.stderr)
    return path
